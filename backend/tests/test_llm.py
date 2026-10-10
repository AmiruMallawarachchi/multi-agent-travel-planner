"""Tests for provider-specific OpenAI-compatible LLM configuration."""

import importlib


def test_groq_configuration_uses_groq_endpoint_and_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ROUTER_MODEL", raising=False)
    monkeypatch.delenv("AGENT_MODEL", raising=False)

    import agents.llm as llm

    llm = importlib.reload(llm)
    settings = llm._client_kwargs(model=llm.AGENT_MODEL, temperature=0.4, streaming=True)

    assert settings["api_key"] == "test-groq-key"
    assert settings["base_url"] == "https://api.groq.com/openai/v1"
    assert llm.AGENT_MODEL == "llama-3.3-70b-versatile"


def test_openai_configuration_remains_supported(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("ROUTER_MODEL", raising=False)
    monkeypatch.delenv("AGENT_MODEL", raising=False)

    import agents.llm as llm

    llm = importlib.reload(llm)
    settings = llm._client_kwargs(model=llm.ROUTER_MODEL, temperature=0, streaming=False)

    assert settings["api_key"] == "test-openai-key"
    assert "base_url" not in settings
    assert llm.ROUTER_MODEL == "gpt-4o-mini"


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unsupported")

    import agents.llm as llm

    try:
        importlib.reload(llm)
    except ValueError as error:
        assert str(error) == "LLM_PROVIDER must be either 'openai' or 'groq'"
    else:
        raise AssertionError("unsupported provider should fail during configuration")
