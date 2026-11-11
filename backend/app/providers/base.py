from abc import ABC, abstractmethod
from typing import Optional


class ProviderUnavailableError(RuntimeError):
    """Raised when configured AI providers are unreachable, rate-limited, or fail."""
    pass


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers in Data Detective.
    Ensures provider-agnostic code generation and reasoning.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'gemini', 'groq', 'mock'."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Verify whether credentials and provider endpoint are configured and accessible."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Generate text response from the model.
        Must raise standard exceptions on rate-limit (429) or timeout to trigger fallback.
        """
        pass
