"""Dataset tester - runs LangFuse dataset items through the agent for evaluation."""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Optional

# Lazy langfuse import
_langfuse: Optional[Any] = None


def _get_langfuse():
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")

    if not secret_key or not public_key:
        raise RuntimeError("LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY must be set")

    from langfuse import Langfuse

    _langfuse = Langfuse(
        secret_key=secret_key,
        public_key=public_key,
        base_url=os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3000"),
    )
    print("✅ Langfuse Initialized")
    return _langfuse


class DatasetTester:
    """Runs dataset items from LangFuse through the agent for evaluation."""

    def __init__(self, dataset_name: str, run_name: Optional[str] = None):
        self.dataset_name = dataset_name
        self.run_name = run_name or f"run-{int(time.time() * 1000)}"

    async def load_dataset_from_langfuse(self, dataset_name: str) -> tuple[list[dict], list[str]]:
        """Load dataset items from LangFuse.

        Returns:
            Tuple of (items, item_ids)
        """
        client = _get_langfuse()
        print(f"📥 Fetching dataset '{dataset_name}'...")

        res = await client.api.dataset_items_list(dataset_name=dataset_name)
        items_data = res.data

        if not items_data or len(items_data) == 0:
            raise ValueError(f"Dataset '{dataset_name}' is empty or not found.")

        print(f"✅ Loaded {len(items_data)} items")

        items = []
        item_ids = []
        for item in items_data:
            input_val = item.input
            if isinstance(input_val, str):
                item_input = input_val
            else:
                import json

                item_input = json.dumps(input_val, ensure_ascii=False)

            expected = item.expected_output
            if isinstance(expected, str):
                expected_output = expected
            elif expected:
                import json

                expected_output = json.dumps(expected, ensure_ascii=False)
            else:
                expected_output = None

            items.append({"input": item_input, "expected_output": expected_output})
            item_ids.append(item.id)

        return items, item_ids

    async def run_single_item(
        self, item: dict, dataset_item_id: str
    ) -> dict[str, Any]:
        """Run a single dataset item through the agent."""
        start = time.time()
        from langchain_core.messages import HumanMessage

        try:
            from ai_app.agent.graph import get_agent

            agent = await get_agent()

            thread_id = f"dataset-test-{dataset_item_id}-{int(time.time() * 1000)}"

            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=item["input"])]},
                config={"configurable": {"thread_id": thread_id}},
            )

            # Find last AI message
            last_ai = None
            for msg in reversed(result.get("messages", [])):
                if getattr(msg, "type", None) == "ai":
                    last_ai = msg
                    break

            import json

            output = (
                json.dumps(
                    {
                        "content": last_ai.content if hasattr(last_ai, "content") else str(last_ai.content),
                        "tool_calls": getattr(last_ai, "tool_calls", []) or [],
                    },
                    ensure_ascii=False,
                )
                if last_ai
                else "{}"
            )

            duration = time.time() - start
            trace_id = result.get("export_trace_id")

            print(f"🧵 Agent execution completed, traceId: {trace_id}")

            # Score in LangFuse
            if trace_id:
                from ai_app.utils.judge_model import model_judge_evaluator

                evaluations = await model_judge_evaluator(
                    input_text=item["input"],
                    output=output,
                    expected_output=item.get("expected_output"),
                )

                client = _get_langfuse()
                for eval_result in evaluations:
                    client.score(
                        trace_id=trace_id,
                        name=eval_result["name"],
                        value=eval_result["value"],
                        comment=eval_result.get("comment"),
                    )

                # Bind dataset item
                await client.api.dataset_run_items_create(
                    dataset_item_id=dataset_item_id,
                    run_name=self.run_name,
                    trace_id=trace_id,
                )

                print(f"📌 DatasetRunItem uploaded for {dataset_item_id} with traceId: {trace_id}")

            return {
                "input": item["input"],
                "output": output,
                "expected_output": item.get("expected_output"),
                "duration": duration,
                "evaluations": evaluations if trace_id else [],
            }

        except Exception as e:
            import traceback

            traceback.print_exc()
            return {
                "input": item["input"],
                "output": "",
                "expected_output": item.get("expected_output"),
                "duration": time.time() - start,
                "error": str(e),
                "evaluations": [],
            }

    async def run_local_experiment(
        self, items: list[dict], item_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Run all dataset items sequentially."""
        print(f"🚀 Dataset Run Created: {self.run_name}")

        results = []
        total = len(items)
        for i, (item, item_id) in enumerate(zip(items, item_ids)):
            print(f"▶️ Running item {i + 1}/{total}")
            res = await self.run_single_item(item, item_id)
            results.append(res)
            await self._sleep(0.25)

        print(f"\n🎉 All Done. Open Langfuse to inspect traces & dataset run.")
        return results

    async def _sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio

        await asyncio.sleep(seconds)
