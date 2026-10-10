"""
agents/llm.py
LLM initialisation (SRS section 1.4 - "LLM provider your choice").

The application uses LangChain's OpenAI-compatible chat client. This supports
OpenAI directly and providers such as Groq through its compatible endpoint,
without making the graph or agent code provider-aware.
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()

if LLM_PROVIDER not in {"openai", "groq"}:
    raise ValueError("LLM_PROVIDER must be either 'openai' or 'groq'")

_DEFAULT_MODEL = "llama-3.3-70b-versatile" if LLM_PROVIDER == "groq" else "gpt-4o-mini"

# Small, cheap, deterministic model for the routing decision - it only ever
# outputs one word, so there's no reason to pay for a bigger model here.
ROUTER_MODEL = os.getenv("ROUTER_MODEL", _DEFAULT_MODEL)

# Model that composes the traveller-facing answers and drives tool calling.
AGENT_MODEL = os.getenv("AGENT_MODEL", _DEFAULT_MODEL)


def _client_kwargs(*, model: str, temperature: float, streaming: bool) -> dict[str, object]:
    """Build provider-specific settings for the OpenAI-compatible client."""
    if LLM_PROVIDER == "groq":
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    else:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "")

    kwargs: dict[str, object] = {
        "model": model,
        "temperature": temperature,
        "streaming": streaming,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return kwargs


def get_router_llm() -> ChatOpenAI:
    """classify_intent's model: temperature 0, no tools, single-label output."""
    return ChatOpenAI(**_client_kwargs(model=ROUTER_MODEL, temperature=0, streaming=False))


def get_agent_llm(*, streaming: bool = True) -> ChatOpenAI:
    """Specialist / general-QA model. Streaming is on by default so FastAPI's
    astream_events bridge (main.py) can forward tokens to the frontend as
    they're generated rather than waiting for the full reply."""
    return ChatOpenAI(**_client_kwargs(model=AGENT_MODEL, temperature=0.4, streaming=streaming))
