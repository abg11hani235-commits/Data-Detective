import asyncio
from typing import Optional
from app.config import settings
from app.logging import logger
from app.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.GEMINI_MODEL or "gemini-2.0-flash"
        self._client = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model_name)
            except Exception as e:
                logger.warning(f"Failed to configure Gemini client: {e}")

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

        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System Instructions:\n{system_instruction}\n\nTask:\n{prompt}"

        # Run with timeout to prevent hung requests
        try:
            loop = asyncio.get_running_loop()
            generation_config = {"temperature": temperature}

            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._client.generate_content(
                        full_prompt,
                        generation_config=generation_config,
                    ),
                ),
                timeout=10.0,
            )
            return response.text
        except asyncio.TimeoutError:
            raise TimeoutError("Gemini request timed out after 10 seconds.")
        except Exception as e:
            logger.error(f"Gemini generation error: {type(e).__name__}")
            raise
