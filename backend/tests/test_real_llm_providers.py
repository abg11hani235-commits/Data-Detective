import pytest
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.config import settings

has_gemini = bool(settings.GEMINI_API_KEY)
has_groq = bool(settings.GROQ_API_KEY)


@pytest.mark.asyncio
@pytest.mark.skipif(not has_gemini, reason="GEMINI_API_KEY not configured in environment")
async def test_live_gemini_provider():
    provider = GeminiProvider()
    assert await provider.is_available() is True
    try:
        res = await provider.generate("Compute 5 + 7 and return just the integer number.")
        assert "12" in res
    except Exception as e:
        # Check if Google's live API responded with rate limit / quota exhaustion / timeout
        error_name = type(e).__name__
        error_msg = str(e)
        assert (
            "ResourceExhausted" in error_name
            or "quota" in error_msg.lower()
            or "429" in error_msg
            or "timeout" in error_msg.lower()
            or "Timeout" in error_name
        ), (
            f"Unexpected Gemini failure: {error_name}: {error_msg}"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not has_groq, reason="GROQ_API_KEY not configured in environment")
async def test_live_groq_provider():
    provider = GroqProvider()
    assert await provider.is_available() is True
    res = await provider.generate("Compute 5 + 7 and return just the integer number.")
    assert "12" in res
