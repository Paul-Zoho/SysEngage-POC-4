"""
Anthropic AI client setup for SysEngage.

Per Row 4 Applied §3 technology stack: Claude Sonnet via Anthropic API.
API key read from ANTHROPIC_API_KEY environment variable at startup.

Usage:
    from core.ai_client import get_ai_client
    client = get_ai_client()
    response = client.messages.create(...)

The client is initialised lazily on first call and reused thereafter.
"""

import os
from anthropic import Anthropic

_client: Anthropic | None = None

MODEL = "claude-sonnet-4-5"


def get_ai_client() -> Anthropic:
    """
    Return the shared Anthropic client, initialising it on first call.

    Raises RuntimeError if ANTHROPIC_API_KEY is not set.
    """
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Set it in Replit Secrets before running AI-involving mechanisms."
            )
        _client = Anthropic(api_key=api_key)
    return _client
