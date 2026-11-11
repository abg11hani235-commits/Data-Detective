import asyncio
from typing import Optional
from app.config import settings
from app.logging import logger
from app.providers.base import LLMProvider


class GroqProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model_name = model or settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        self._client = None
        if self.api_key:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to configure Groq client: {e}")

    @property
    def name(self) -> str:
        return "groq"

    async def is_available(self) -> bool:
        return bool(self.api_key and self._client)

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        if not await self.is_available():
            raise RuntimeError("Groq API key is not configured or client initialization failed.")

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        try:
            chat_completion = await asyncio.wait_for(
                self._client.chat.completions.create(
                    messages=messages,
                    model=self.model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=20.0,
            )
            return chat_completion.choices[0].message.content or ""
        except asyncio.TimeoutError:
            raise TimeoutError("Groq request timed out after 20 seconds.")
        except Exception as e:
            logger.error(f"Groq generation error: {type(e).__name__}")
            raise
