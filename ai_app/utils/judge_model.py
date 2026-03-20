"""Judge model - evaluates agent output quality using a separate LLM."""

from __future__ import annotations

import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from ai_app.config.prompts import get_system_prompt

JUDGE_USE_LOCAL = False


def _create_zhipu_judge_model() -> ChatOpenAI:
    """Create the judge model (Zhipu-style via ChatOpenAI-compatible API)."""
    return ChatOpenAI(
        model=os.environ.get("LLM_MODEL_NAME", "gpt-4"),
        temperature=0.1,
        openai_api_key=os.environ.get("OPENAI_API_KEY", "EMPTY"),
        base_url=os.environ.get("LLM_BASE_URL"),
    )


async def _call_zhipu_judge_model(system_prompt: str, user_prompt: str) -> str:
    model = _create_zhipu_judge_model()
    from langchain_core.messages import HumanMessage, SystemMessage

    msg = await model.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    return msg.content if hasattr(msg, "content") else str(msg.content)


async def _call_local_judge_model(system_prompt: str, user_prompt: str) -> str:
    import httpx

    url = os.environ.get("LOCAL_LLM_URL")
    if not url:
        raise RuntimeError("LOCAL_LLM_URL not set")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            json={
                "model": os.environ.get("LOCAL_LLM_MODEL", "local-judge-model"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def call_judge_model(system_prompt: str, user_prompt: str) -> str:
    """Call the judge model (auto-selects local or remote)."""
    if JUDGE_USE_LOCAL:
        return await _call_local_judge_model(system_prompt, user_prompt)
    return await _call_zhipu_judge_model(system_prompt, user_prompt)


async def model_judge_evaluator(
    input_text: str,
    output: str,
    expected_output: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Evaluate agent output quality.

    Args:
        input_text: The user input.
        output: The agent's response.
        expected_output: Optional expected response.

    Returns:
        List of evaluation results with name, value, and comment.
    """
    system_prompt = str(await get_system_prompt("ZLT_JUDGE"))

    user_prompt = f"""请作为严格的 AI 评审官，根据以下内容为模型输出打分。

  Input:
  {input_text}

  Model Output:
  {output}

  Expected Output:
  {expected_output or '(无)'}""".strip()

    judge_raw = await call_judge_model(system_prompt, user_prompt)

    try:
        import json

        parsed = json.loads(judge_raw)
        return [
            {
                "name": "score",
                "value": float(parsed.get("score", 0)),
                "comment": parsed.get("comment", "无评论"),
            }
        ]
    except Exception:
        return [
            {
                "name": "score",
                "value": 0.0,
                "comment": f"无法解析裁判模型输出：{judge_raw}",
            }
        ]
