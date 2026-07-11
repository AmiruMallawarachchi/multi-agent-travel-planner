"""
agents/llm.py
LLM initialisation (SRS section 1.4 - "LLM provider your choice").

Provider is OpenAI. Kept behind two small factory functions so swapping
providers later (Anthropic, Groq, ...) means editing this file only -
nothing in nodes.py, graph.py, or prompts.py needs to know or care.
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

# Small, cheap, deterministic model for the routing decision - it only ever
# outputs one word, so there's no reason to pay for a bigger model here.
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")

# Model that composes the traveller-facing answers and drives tool calling.
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")


def get_router_llm() -> ChatOpenAI:
    """classify_intent's model: temperature 0, no tools, single-label output."""
    return ChatOpenAI(model=ROUTER_MODEL, temperature=0)


def get_agent_llm(*, streaming: bool = True) -> ChatOpenAI:
    """Specialist / general-QA model. Streaming is on by default so FastAPI's
    astream_events bridge (main.py) can forward tokens to the frontend as
    they're generated rather than waiting for the full reply."""
    return ChatOpenAI(model=AGENT_MODEL, temperature=0.4, streaming=streaming)
