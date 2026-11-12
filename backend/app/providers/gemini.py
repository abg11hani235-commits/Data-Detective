import asyncio
import logging
from typing import Optional

from app.config import settings
from app.providers.base import LLMProvider

logger = logging.getLogger("data_detective.providers.gemini")


class GeminiProvider(LLMProvider):
    """
    Modern Gemini LLM Provider using the official google-genai SDK.
    Replaces deprecated google.generativeai package.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        # Normalize model name with models/ prefix if missing
        raw_model = model or settings.GEMINI_MODEL or "models/gemini-3.1-flash-lite"
        if not raw_model.startswith("models/"):
            raw_model = f"models/{raw_model}"
        self.model_name = raw_model
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}")

    @property
    def name(self) -> str:
        return "gemini"

    async def is_available(self) -> bool:
        return bool(self.api_key and self._client)

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        if not await self.is_available():
            raise RuntimeError("Gemini API key is not configured or client initialization failed.")

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        try:
            # Use async API of google-genai
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                ),
                timeout=25.0,
            )
            return response.text
        except asyncio.TimeoutError:
            raise TimeoutError("Gemini request timed out after 25 seconds.")
        except Exception as e:
            logger.error(f"Gemini generation error: {type(e).__name__} - {e}")
            raise
