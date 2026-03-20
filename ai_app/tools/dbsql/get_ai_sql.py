"""AI SQL generation tool - uses an external LLM to convert natural language to SQL."""

import os
from typing import Optional

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class GetAiSqlInput(BaseModel):
    question: str = Field(description="用户问句,禁止修改")
    previous_error: Optional[str] = Field(
        default=None,
        description="之前生成的SQL和之前SQL执行的错误信息,用于修正SQL",
    )
    previous_sql: Optional[str] = Field(
        default=None,
        description="之前生成的SQL,用于修正SQL",
    )

    model_config = {"populate_by_name": True}


async def _call_stock_select(question: str, previous_error: Optional[str] = None) -> dict:
    """Call the AI SQL generation API."""
    url = os.environ.get("AI_SQL_URL")
    if not url:
        return {"error": "AI_SQL_URL environment variable not set"}

    payload: dict = {"question": question}
    if previous_error:
        payload["previousError"] = previous_error

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {e}"}
        except Exception as e:
            return {"error": str(e)}

    if result.get("error"):
        return {"error": result["error"], "sql": result.get("sql", "")}

    return {
        "sql": result.get("sql", ""),
        "rows": result.get("result", []),
    }


@tool(args_schema=GetAiSqlInput)
def get_ai_sql(input: GetAiSqlInput) -> dict:
    """查询股票数据库,生成SQL语句。

    如果之前 executeSql 工具执行失败,将错误信息传入 previousError 参数,
    将之前的 sql 传入 previousSql 参数。
    """
    question = input.question
    previous_error = input.previous_error
    previous_sql = input.previous_sql

    # 如果有错误信息，将错误信息拼接在用户问题后面
    if previous_error and previous_sql:
        question = (
            f"{question}\n\n"
            f"之前生成的SQL: {previous_sql}\n"
            f"以及SQL执行的错误: {previous_error}, 请根据这些信息生成正确的SQL。"
        )

    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(_call_stock_select(question))
    return result
