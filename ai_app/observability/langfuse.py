"""LangFuse observability - trace and span management for the agent."""

from __future__ import annotations

import sys
from typing import Any, Optional

from ai_app.config.settings import settings

# Module-level singleton
_langfuse_handler: Optional[Any] = None


def _get_langfuse_handler() -> Optional[Any]:
    """Get or initialize the Langfuse callback handler singleton."""
    global _langfuse_handler
    if _langfuse_handler is not None:
        return _langfuse_handler

    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        print("⚠️ Langfuse credentials not found. Tracing disabled.", file=sys.stderr)
        return None

    try:
        from langfuse import Langfuse

        client = Langfuse(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_BASE_URL,
        )
        # Langfuse v3: use CallbackHandler
        from langfuse.langchain.CallbackHandler import CallbackHandler

        _langfuse_handler = CallbackHandler(client=client)
        print("✅ Langfuse handler initialized")
        return _langfuse_handler
    except Exception as e:
        print(f"⚠️ Failed to initialize Langfuse: {e}", file=sys.stderr)
        return None


def initialize_langfuse() -> None:
    """Initialize Langfuse client (no-op if already initialized)."""
    _get_langfuse_handler()


def is_langfuse_initialized() -> bool:
    """Check if Langfuse handler is initialized."""
    return _langfuse_handler is not None


def init_trace_node(state: dict, config: Optional[dict] = None) -> dict:
    """LangGraph node: initialize a Langfuse trace for the session.

    Langfuse v3 uses CallbackHandler passed via LLM config callbacks.
    """
    handler = _get_langfuse_handler()
    if handler is None:
        return state

    if state.get("trace_id"):
        return state

    return {
        **state,
        "_langfuse_handler": handler,
    }


def finalize_trace_node(state: dict) -> dict:
    """LangGraph node: finalize the Langfuse trace."""
    return state


def get_trace(state: dict) -> Any:
    """Get Langfuse handler from state for use in LLM callbacks."""
    return state.get("_langfuse_handler")
