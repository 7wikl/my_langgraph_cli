"""LangFuse observability - trace and span management for the agent."""

from __future__ import annotations

import os
import sys
from typing import Any, Optional

# Module-level singleton
_langfuse_client: Optional[Any] = None


def _get_langfuse_client() -> Any:
    """Get or initialize the LangFuse client singleton."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client

    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")

    if not secret_key or not public_key:
        print("⚠️ LangFuse credentials not found. Tracing disabled.", file=sys.stderr)
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            base_url=os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3000"),
        )
        print("✅ LangFuse client initialized")
        return _langfuse_client
    except Exception as e:
        print(f"⚠️ Failed to initialize LangFuse: {e}", file=sys.stderr)
        return None


def initialize_langfuse() -> None:
    """Initialize LangFuse client (no-op if already initialized)."""
    _get_langfuse_client()


def is_langfuse_initialized() -> bool:
    """Check if LangFuse client is initialized."""
    return _langfuse_client is not None


def get_trace(state: dict) -> Any:
    """Get a LangFuse trace object for the given state.

    Args:
        state: The agent state dict containing trace_id.

    Returns:
        A LangFuse trace object or None if not initialized.
    """
    client = _get_langfuse_client()
    if client is None:
        return None
    trace_id = state.get("trace_id")
    if not trace_id:
        return None
    return client.trace(id=trace_id)


def init_trace_node(state: dict, context: Any) -> dict:
    """LangGraph node: initialize a LangFuse trace for the session.

    Args:
        state: Current agent state.
        context: LangGraph runtime context.

    Returns:
        Updated state with trace_id and session_id.
    """
    initialize_langfuse()

    client = _get_langfuse_client()
    if client is None:
        return state

    # Already created → skip
    if state.get("trace_id"):
        return state

    thread_id = context.configurable.get("thread_id") if context.configurable else None
    session_id = thread_id or f"session_{int(__import__('time').time() * 1000)}"

    # Find last user message
    user_content = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = getattr(msg, "type", None) or msg.get("type")
        if msg_type == "human":
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            user_content = content if isinstance(content, str) else str(content)
            break

    trace = client.trace(
        name="financial-agent",
        input=user_content,
        session_id=session_id,
        user_id="default-user",
        metadata={"start_time": __import__("datetime").datetime.now().isoformat()},
    )

    return {
        **state,
        "trace_id": trace.id,
        "session_id": session_id,
    }


def finalize_trace_node(state: dict) -> dict:
    """LangGraph node: finalize the LangFuse trace.

    Args:
        state: Current agent state.

    Returns:
        Updated state with export_trace_id and cleared trace_id.
    """
    trace = get_trace(state)
    if trace is None:
        return state

    messages = state.get("messages", [])
    last = messages[-1] if messages else None

    output: Optional[str] = None
    if last:
        content = last.content if hasattr(last, "content") else last.get("content")
        if content:
            output = content if isinstance(content, str) else __import__("json").dumps(content, ensure_ascii=False)

    trace.update(
        output=output,
        metadata={
            "end_time": __import__("datetime").datetime.now().isoformat(),
            "llm_calls": state.get("llm_calls", 0),
        },
    )

    return {
        **state,
        "trace_id": None,  # Prevent leakage
        "export_trace_id": trace.id,
    }
