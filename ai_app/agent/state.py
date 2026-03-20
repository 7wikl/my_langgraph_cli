"""Agent state definitions using LangGraph TypedDict."""

from __future__ import annotations

from typing import Annotated, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(dict):
    """LangGraph state for the financial agent.

    This TypedDict tracks:
    - messages: conversation history (appended via add_messages reducer)
    - llm_calls: number of LLM invocations
    - session_id / trace_id / export_trace_id: observability tracking
    - conversation_summary: summarized history (for context window management)
    - messages_summarized_count: index of last summarized message
    - sql_retry_count / last_sql_error / last_user_question / last_generated_sql: SQL retry state
    - sql_max_retries_exceeded: flag when SQL retries are exhausted
    """

    messages: Annotated[list[BaseMessage], add_messages]
    llm_calls: int
    session_id: Optional[str]
    trace_id: Optional[str]
    export_trace_id: Optional[str]
    conversation_summary: Optional[str]
    last_summary_at_call: Optional[int]
    messages_summarized_count: Optional[int]
    sql_retry_count: Optional[int]
    last_sql_error: Optional[str]
    last_user_question: Optional[str]
    last_generated_sql: Optional[str]
    sql_max_retries_exceeded: Optional[bool]
