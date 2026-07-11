"""
agents/llm.py
LLM factory for TripWeaver.
All agents use this single factory so the model/provider is configured once.
"""

from __future__ import annotations
import os
from functools import lru_cache
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_llm(streaming: bool = False) -> ChatOpenAI:
    """
    Return a ChatOpenAI instance configured from environment variables.

    Parameters
    ----------
    streaming : bool
        Set True when the caller wants token-by-token streaming (e.g., the
        final response nodes).  Intent detection uses streaming=False.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_openai_api_key_here":
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        streaming=streaming,
        api_key=api_key,
    )
