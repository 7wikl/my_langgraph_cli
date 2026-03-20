"""SQL execution tool - executes generated SQL against the stock database."""

import os

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ExecuteSqlInput(BaseModel):
    sql: str = Field(description="标准的sql语句")


async def _execute_sql(sql: str) -> dict:
    """Execute SQL against the database via HTTP API."""
    url = os.environ.get("EXECUTE_SQL_URL")
    if not url:
        return {"error": "EXECUTE_SQL_URL environment variable not set", "success": False}

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("ASSET_CONTROL_KEY")
    if api_key:
        headers["X-MCP-API-KEY"] = api_key

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json={"sql": sql}, headers=headers)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {e}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    if result.get("success") is True:
        return {"data": result.get("data", result), "success": True}
    else:
        return {
            "error": result.get("error", "SQL执行失败,未知错误"),
            "sql": sql,
            "success": False,
        }


@tool(args_schema=ExecuteSqlInput)
def execute_sql(input: ExecuteSqlInput) -> dict:
    """执行SQL查询数据库,获取到SQL之后就调用此工具。"""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(_execute_sql(input.sql))
        return result
    except Exception as e:
        return {
            "error": str(e),
            "sql": input.sql,
            "success": False,
        }
