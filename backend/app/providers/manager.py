import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.config import settings
from app.logging import logger
from app.providers.base import LLMProvider, ProviderUnavailableError
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.mock import HeuristicProvider


class ProviderManager:
    """
    Manages LLM providers with automatic fallback, timeout handling,
    latency tracking, and safe user notification.
    """

    def __init__(
        self,
        gemini: Optional[LLMProvider] = None,
        groq: Optional[LLMProvider] = None,
        mock: Optional[LLMProvider] = None,
    ):
        self.gemini = gemini or GeminiProvider()
        self.groq = groq or GroqProvider()
        self.mock = mock or HeuristicProvider()
        self.last_fallback_triggered: bool = False
        self.last_telemetry: Dict[str, Any] = {}

    def get_providers_order(self) -> List[LLMProvider]:
        if settings.PRIMARY_LLM_PROVIDER.lower() == "groq":
            return [self.groq, self.gemini]
        return [self.gemini, self.groq]

    def is_mock_allowed(self) -> bool:
        # In production, never allow silent mock fallback
        if settings.APP_ENV == "production":
            return False
        return settings.ALLOW_MOCK_FALLBACK

    async def generate_with_fallback(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        on_status_update: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        """
        Executes generation attempting the primary provider first, cascading to fallback upon failure.
        Returns tuple of (response_text, provider_name_used).
        Raises ProviderUnavailableError if real configured providers fail and mock fallback is disabled.
        """
        providers = self.get_providers_order()
        self.last_fallback_triggered = False
        attempted_real_providers: List[str] = []
        errors: List[str] = []

        start_time = time.time()

        for idx, provider in enumerate(providers):
            # Check if provider is configured and available
            if not await provider.is_available():
                continue

            attempted_real_providers.append(provider.name)
            try:
                if idx > 0:
                    self.last_fallback_triggered = True
                    if on_status_update:
                        on_status_update(f"Primary model unavailable. Switching to fallback provider ({provider.name}).")

                logger.info(f"Invoking LLM provider: {provider.name}")
                provider_start = time.time()
                response = await provider.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=temperature,
                )
                duration_ms = round((time.time() - provider_start) * 1000, 2)
                self.last_telemetry = {
                    "provider": provider.name,
                    "latency_ms": duration_ms,
                    "fallback_triggered": self.last_fallback_triggered,
                    "is_mock": False,
                }
                return response, provider.name
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {type(e).__name__} - {e}")
                errors.append(f"{provider.name}: {type(e).__name__}")
                continue

        # If real providers were attempted and all failed:
        if attempted_real_providers:
            logger.error(f"All attempted AI providers failed: {errors}")
            if not self.is_mock_allowed():
                raise ProviderUnavailableError(
                    "Primary and fallback AI providers are currently unavailable. Unable to complete analysis."
                )

        # If mock fallback is permitted in development:
        if self.is_mock_allowed():
            if attempted_real_providers:
                logger.info("Real providers failed; operating with deterministic heuristic engine as development fallback.")
                if on_status_update:
                    on_status_update("External AI providers unavailable. Operating with deterministic analytical engine.")
            else:
                logger.info("External LLM credentials not configured. Operating with deterministic analytical engine.")
                if on_status_update:
                    on_status_update("External LLM not configured. Operating with deterministic analytical engine.")

            mock_start = time.time()
            response = await self.mock.generate(prompt=prompt, system_instruction=system_instruction, temperature=temperature)
            duration_ms = round((time.time() - mock_start) * 1000, 2)
            self.last_telemetry = {
                "provider": self.mock.name,
                "latency_ms": duration_ms,
                "fallback_triggered": True,
                "is_mock": True,
            }
            return response, self.mock.name

        raise ProviderUnavailableError(
            "No AI providers configured. Please provide GEMINI_API_KEY or GROQ_API_KEY."
        )


provider_manager = ProviderManager()
