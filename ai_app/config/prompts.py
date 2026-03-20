"""Prompt configuration - uses local system prompts only."""

from datetime import datetime

from .prompts_local import FINANCIAL_AGENT_SYSTEM_PROMPT


def get_system_prompt(name: str = "FINANCIAL_AGENT_SYSTEM_PROMPT") -> str:
    """Get system prompt from local file.

    Args:
        name: Prompt name (unused, kept for compatibility).

    Returns:
        The system prompt string with today's date prepended.
    """
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"今天的日期是:{today}, {FINANCIAL_AGENT_SYSTEM_PROMPT}"
