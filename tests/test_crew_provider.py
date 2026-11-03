from app.config.settings import settings
from app.investigation.crew import _build_configured_llm


class FakeCrewAI:
    @staticmethod
    def LLM(**options):
        return options


def test_groq_llm_uses_backend_settings_without_exposing_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "llm_model", "llama-3.3-70b-versatile")
    monkeypatch.setattr(settings, "llm_api_key", "server-only-test-secret")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(settings, "llm_temperature", 0.2)
    monkeypatch.setattr(settings, "llm_max_tokens", 2000)

    llm_options = _build_configured_llm(FakeCrewAI)

    assert llm_options == {
        "model": "groq/llama-3.3-70b-versatile",
        "api_key": "server-only-test-secret",
        "temperature": 0.2,
        "max_tokens": 2000,
        "base_url": "https://api.groq.com/openai/v1",
    }


def test_groq_llm_is_not_created_without_server_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "llm_model", "llama-3.3-70b-versatile")
    monkeypatch.setattr(settings, "llm_api_key", "")

    assert _build_configured_llm(FakeCrewAI) is None
