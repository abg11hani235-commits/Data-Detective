import asyncio
import pytest
from app.config import settings
from app.providers.base import LLMProvider, ProviderUnavailableError
from app.providers.manager import ProviderManager


class MockSuccessProvider(LLMProvider):
    def __init__(self, name: str, return_text: str = "mock output"):
        self._name = name
        self.return_text = return_text

    @property
    def name(self) -> str:
        return self._name

    async def is_available(self) -> bool:
        return True

    async def generate(self, prompt: str, system_instruction=None, temperature=0.2) -> str:
        return self.return_text


class MockFailingProvider(LLMProvider):
    def __init__(self, name: str, error_to_raise: Exception = RuntimeError("Rate limit exceeded")):
        self._name = name
        self.error_to_raise = error_to_raise

    @property
    def name(self) -> str:
        return self._name

    async def is_available(self) -> bool:
        return True

    async def generate(self, prompt: str, system_instruction=None, temperature=0.2) -> str:
        raise self.error_to_raise


@pytest.mark.asyncio
async def test_case_a_gemini_succeeds(monkeypatch):
    """Case A: Gemini succeeds as primary, provider_used = 'gemini', no fallback."""
    monkeypatch.setattr(settings, "PRIMARY_LLM_PROVIDER", "gemini")
    gemini = MockSuccessProvider("gemini", "Gemini analysis")
    groq = MockSuccessProvider("groq", "Groq analysis")
    manager = ProviderManager(gemini=gemini, groq=groq)

    status_events = []
    response, provider = await manager.generate_with_fallback(
        "test question",
        on_status_update=lambda msg: status_events.append(msg)
    )

    assert provider == "gemini"
    assert response == "Gemini analysis"
    assert manager.last_fallback_triggered is False
    assert len(status_events) == 0


@pytest.mark.asyncio
async def test_case_b_gemini_fails_groq_succeeds(monkeypatch):
    """Case B: Gemini fails with timeout or rate limit, Groq succeeds, fallback_triggered = True."""
    monkeypatch.setattr(settings, "PRIMARY_LLM_PROVIDER", "gemini")
    gemini = MockFailingProvider("gemini", TimeoutError("Gemini timed out after 25s"))
    groq = MockSuccessProvider("groq", "Groq fallback analysis")
    manager = ProviderManager(gemini=gemini, groq=groq)

    status_events = []
    response, provider = await manager.generate_with_fallback(
        "test question",
        on_status_update=lambda msg: status_events.append(msg)
    )

    assert provider == "groq"
    assert response == "Groq fallback analysis"
    assert manager.last_fallback_triggered is True
    assert any("Switching to fallback provider (groq)" in s for s in status_events)


@pytest.mark.asyncio
async def test_case_groq_fails_gemini_succeeds(monkeypatch):
    """Case B2: Groq fails as primary, Gemini succeeds as fallback."""
    monkeypatch.setattr(settings, "PRIMARY_LLM_PROVIDER", "groq")
    groq = MockFailingProvider("groq", TimeoutError("Groq timed out"))
    gemini = MockSuccessProvider("gemini", "Gemini fallback analysis")
    manager = ProviderManager(gemini=gemini, groq=groq)

    status_events = []
    response, provider = await manager.generate_with_fallback(
        "test question",
        on_status_update=lambda msg: status_events.append(msg)
    )

    assert provider == "gemini"
    assert response == "Gemini fallback analysis"
    assert manager.last_fallback_triggered is True
    assert any("Switching to fallback provider (gemini)" in s for s in status_events)


@pytest.mark.asyncio
async def test_case_c_both_providers_fail_clean_error():
    """Case C: Both Gemini and Groq fail. Must raise ProviderUnavailableError without leaking keys or stack trace."""
    gemini = MockFailingProvider("gemini", RuntimeError("Gemini 429 quota exhausted"))
    groq = MockFailingProvider("groq", TimeoutError("Groq 504 gateway timeout"))
    manager = ProviderManager(gemini=gemini, groq=groq)

    # Disable mock fallback to test strict production failure mode
    original_setting = settings.ALLOW_MOCK_FALLBACK
    try:
        settings.ALLOW_MOCK_FALLBACK = False
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await manager.generate_with_fallback("test question")

        err_msg = str(exc_info.value)
        assert "AI providers are currently unavailable" in err_msg
        # Ensure no secrets or internal sensitive details leak in message
        assert "API_KEY" not in err_msg
        assert "AIza" not in err_msg
    finally:
        settings.ALLOW_MOCK_FALLBACK = original_setting
