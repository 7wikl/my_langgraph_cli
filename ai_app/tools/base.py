"""Tools base module - shared tool utilities and registry."""

from __future__ import annotations

from typing import Any, Callable, TypeVar, ParamSpec

from langchain_core.tools import BaseTool
from pydantic import BaseModel

P = ParamSpec("P")
R = TypeVar("R")


def create_tool(
    func: Callable[P, R],
    name: str,
    description: str,
    args_schema: type[BaseModel],
) -> BaseTool:
    """Create a LangChain BaseTool from a function and Pydantic schema.

    Args:
        func: The underlying function to wrap.
        name: Tool name.
        description: Tool description for the LLM.
        args_schema: Pydantic model for input validation.

    Returns:
        A BaseTool instance bound to the function.
    """
    return BaseTool(
        name=name,
        description=description,
        args_schema=args_schema,
        func=func,
    )
