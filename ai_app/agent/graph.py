"""LangGraph agent definition - core state machine for the financial agent."""

from __future__ import annotations

import json
import sys

from ai_app.config.settings import settings
from typing import Any, Literal

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from ai_app.agent.state import AgentState
from ai_app.config.prompts import get_system_prompt
from ai_app.tools.card.kline_card import show_kline_card
from ai_app.tools.dbsql.exec_sql import execute_sql
from ai_app.tools.dbsql.get_ai_sql import get_ai_sql

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

_model: ChatOpenAI | None = None


def _get_model() -> ChatOpenAI:
    """Get or create the ChatOpenAI model instance (lazy singleton)."""
    global _model
    if _model is None:
        _model = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            temperature=0,
            base_url=settings.LLM_BASE_URL or None,
        )
    return _model


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS_BY_NAME: dict[str, Any] = {
    show_kline_card.name: show_kline_card,
    get_ai_sql.name: get_ai_sql,
    execute_sql.name: execute_sql,
}
TOOLS = list(TOOLS_BY_NAME.values())

# ---------------------------------------------------------------------------
# Node: LLM call
# ---------------------------------------------------------------------------


def _llm_call(state: AgentState, config: RunnableConfig | None = None) -> dict:
    """Invoke the LLM with system prompt and current messages."""
    system_prompt = get_system_prompt()

    # Inject conversation summary if available
    messages_for_model = state["messages"]
    if state.get("conversation_summary"):
        system_prompt += f"\n[对话历史总结]: {state['conversation_summary']}"
        start_index = state.get("messages_summarized_count") or 0
        messages_for_model = state["messages"][start_index:]

    llm_input = [SystemMessage(content=system_prompt), *messages_for_model]

    result = _get_model().bind_tools(TOOLS).invoke(llm_input)

    return {
        "messages": [result],
        "llm_calls": (state.get("llm_calls") or 0) + 1,
    }


# ---------------------------------------------------------------------------
# Node: Tool execution
# ---------------------------------------------------------------------------


def _tool_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
    """Execute tool calls from the last AI message."""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if not last_message or not isinstance(last_message, AIMessage):
        return {"messages": []}

    tool_calls = last_message.tool_calls or []
    if not tool_calls:
        return {"messages": []}

    new_messages: list[ToolMessage] = []

    sql_retry_count = state.get("sql_retry_count") or 0
    last_sql_error = state.get("last_sql_error")
    last_user_question = state.get("last_user_question")
    last_generated_sql = state.get("last_generated_sql")

    for tool_call in tool_calls:
        tool = TOOLS_BY_NAME.get(tool_call["name"])
        if not tool:
            raise ValueError(f'Tool "{tool_call["name"]}" not found')

        try:
            observation = tool.invoke(tool_call.get("args"))
            # Serialize (bigint -> str for JSON compatibility)
            content = json.dumps(observation, ensure_ascii=False, default=str)

            # SQL execution error handling: retry up to 3 times
            if tool_call["name"] == execute_sql.name:
                try:
                    parsed = json.loads(content)
                except Exception:
                    parsed = {}

                has_error = parsed.get("error") or parsed.get("message")

                if has_error:
                    sql_retry_count += 1
                    last_sql_error = content

                    if sql_retry_count >= 3:
                        warning = ToolMessage(
                            tool_call_id=tool_call["id"],
                            name=tool_call["name"],
                            content=json.dumps(
                                {
                                    "error": f"SQL执行失败,已重试3次仍未成功。最后错误: {last_sql_error}",
                                    "warning": "无法获取数据，请稍后重试",
                                    "sql": parsed.get("sql", ""),
                                },
                                ensure_ascii=False,
                            ),
                        )
                        new_messages.append(warning)
                        return {
                            "messages": [*messages, *new_messages],
                            "sql_retry_count": 0,
                            "last_sql_error": None,
                            "last_user_question": None,
                            "last_generated_sql": None,
                            "sql_max_retries_exceeded": True,
                        }

                    # Pass error back to LLM for retry
                    error_msg = ToolMessage(
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"],
                        content=json.dumps(
                            {"message": last_sql_error},
                            ensure_ascii=False,
                        ),
                    )
                    new_messages.append(error_msg)
                    continue

            # Save generated SQL from getAiSQL for retry
            if tool_call["name"] == get_ai_sql.name:
                try:
                    parsed = json.loads(content)
                except Exception:
                    parsed = {}
                if parsed.get("sql") and not parsed.get("error"):
                    last_user_question = tool_call.get("args", {}).get("question", last_user_question)
                    last_generated_sql = parsed["sql"]
                    last_sql_error = None

            tool_msg = ToolMessage(
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
                content=content,
            )
            new_messages.append(tool_msg)

        except Exception as e:
            raise

    return {
        "messages": new_messages,
        "sql_retry_count": sql_retry_count,
        "last_sql_error": last_sql_error,
        "last_user_question": last_user_question,
        "last_generated_sql": last_generated_sql,
    }


# ---------------------------------------------------------------------------
# Node: Conversation summarization
# ---------------------------------------------------------------------------


def _summarize_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
    """Summarize older messages to manage context window size."""
    print(f"LLM calls threshold reached ({state.get('llm_calls')}), generating summary...")

    # Find cut point: keep last 6 messages, avoid splitting tool calls
    messages = state.get("messages", [])
    cut_index = len(messages) - 6
    if cut_index < 0:
        cut_index = 0
    while cut_index > 0 and isinstance(messages[cut_index], ToolMessage):
        cut_index -= 1

    start_index = state.get("messages_summarized_count") or 0
    if cut_index <= start_index:
        print("Not enough new messages to summarize. Skipping.")
        return {"last_summary_at_call": state.get("llm_calls")}

    messages_to_summarize = messages[start_index:cut_index]

    # Build summary prompt
    msg_lines = []
    for m in messages_to_summarize:
        content = m.content if hasattr(m, "content") else str(m.get("content", ""))
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False, default=str)
        msg_type = getattr(m, "type", None) or m.get("type", "")
        if msg_type == "human":
            msg_lines.append(f"用户: {content}")
        elif msg_type == "ai":
            msg_lines.append(f"助手: {content}")
        elif msg_type == "tool":
            msg_lines.append(f"工具结果: {content[:100]}...")
        elif msg_type == "system":
            msg_lines.append(f"系统: {content}")

    summary_prompt = [
        SystemMessage(
            content="请简洁地总结以下对话内容,保留关键信息、重要数据和用户意图。总结应该在200字以内。"
        ),
        HumanMessage(
            content=(
                f"之前的对话总结：{state.get('conversation_summary') or '无'}\n\n"
                f"需要总结的对话：\n" + "\n".join(msg_lines)
            )
        ),
    ]

    try:
        summary_result = _get_model().invoke(summary_prompt)
        new_summary = (
            summary_result.content
            if hasattr(summary_result, "content")
            else str(summary_result)
        )

        print(f"Summary generated. Updated summary covering up to index {cut_index}.")

        return {
            "conversation_summary": new_summary,
            "last_summary_at_call": state.get("llm_calls"),
            "messages_summarized_count": cut_index,
        }
    except Exception as e:
        print(f"❌ Summary generation failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# Node: Error handler (SQL retries exhausted)
# ---------------------------------------------------------------------------


def _error_handler(state: AgentState, config: RunnableConfig | None = None) -> dict:
    """Generate a friendly error message when SQL retries are exhausted."""
    last_sql_error = state.get("last_sql_error") or "未知错误"

    error_prompt = [
        SystemMessage(
            content="你是一位专业的金融数据助手。由于技术原因，当前无法获取用户请求的数据。"
            "请用友好、专业的语气向用户解释这个问题，并建议用户稍后重试或换个方式提问。"
            "不要提及SQL或技术细节。"
        ),
        HumanMessage(content=f"很抱歉，查询数据时遇到了问题。错误信息：{last_sql_error}"),
    ]

    result = _get_model().invoke(error_prompt)

    return {
        "messages": [result],
        "llm_calls": (state.get("llm_calls") or 0) + 1,
        "sql_retry_count": 0,
        "last_sql_error": None,
        "last_user_question": None,
        "last_generated_sql": None,
        "sql_max_retries_exceeded": False,
    }


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------


def _should_continue(state: AgentState) -> Literal["toolNode", "errorHandler", "finalizeTrace"]:
    """Decide which node to route to after llmCall."""
    llm_calls = state.get("llm_calls") or 0

    # 50 calls -> force end
    if llm_calls >= 50:
        return "finalizeTrace"

    # SQL retries exhausted -> error handler
    if state.get("sql_max_retries_exceeded"):
        return "errorHandler"

    messages = state.get("messages", [])
    last = messages[-1] if messages else None
    if not last or not isinstance(last, AIMessage):
        return "finalizeTrace"

    if last.tool_calls:
        return "toolNode"

    return "finalizeTrace"


def _should_summarize(state: AgentState) -> Literal["summarizeNode", "llmCall"]:
    """Decide whether to summarize after tool execution."""
    current = state.get("llm_calls") or 0
    last_summary = state.get("last_summary_at_call") or 0
    if (current - last_summary) >= 10:
        print(f"🔍 Summary check: {current} calls (last summary at {last_summary}) - triggering summary")
        return "summarizeNode"
    return "llmCall"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

_compiled_graph: Any = None


async def create_agent() -> Any:
    """Build and return the compiled LangGraph agent with PostgreSQL checkpointer."""
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    # Build the graph
    graph = (
        StateGraph(AgentState)
        # .add_node("initTrace", lambda state, config=None: state)
        .add_node("llmCall", _llm_call)
        .add_node("toolNode", _tool_node)
        .add_node("summarizeNode", _summarize_node)
        .add_node("errorHandler", _error_handler)
        .add_node("finalizeTrace", lambda state, config=None: state)
        .add_edge(START, "llmCall")
        # .add_edge("initTrace", "llmCall")
        .add_conditional_edges(
            "llmCall",
            _should_continue,
            {"toolNode": "toolNode", "errorHandler": "errorHandler", "finalizeTrace": "finalizeTrace"},
        )
        .add_conditional_edges(
            "toolNode",
            _should_summarize,
            {"summarizeNode": "summarizeNode", "llmCall": "llmCall"},
        )
        .add_edge("summarizeNode", "llmCall")
        .add_edge("errorHandler", "finalizeTrace")
        .add_edge("finalizeTrace", END)
    )

    # PostgreSQL checkpointer (optional - skip if URI not configured)
    checkpointer = None
    postgres_uri = settings.POSTGRES_DATABASE_URI
    if postgres_uri:
        try:
            from langgraph.checkpoint.postgres import AsyncPostgresSaver

            checkpointer = AsyncPostgresSaver.from_conn_string(postgres_uri)
        except Exception as e:
            print(f"⚠️ Failed to initialize Postgres checkpointer: {e}", file=sys.stderr)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    _compiled_graph = graph.compile(**compile_kwargs)
    return _compiled_graph


async def get_agent() -> Any:
    """Get the compiled agent graph (creates it if needed)."""
    return await create_agent()
