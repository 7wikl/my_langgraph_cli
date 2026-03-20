"""FastAPI route definitions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ai_app.agent.graph import get_agent
from ai_app.api.schemas import (
    ChatRequest,
    ErrorResponse,
    HealthResponse,
    TestDatasetRequest,
    TestDatasetResponse,
)
from ai_app.utils.dataset_tester import DatasetTester

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        message="Fin Agent API is running",
    )


@router.get("/api/healthz")
async def healthz() -> dict:
    """Kubernetes-style health endpoint."""
    return {"status": "ok"}


@router.post("/agent/chat")
async def chat(request: ChatRequest) -> JSONResponse:
    """Main chat endpoint - invoke the financial agent."""
    try:
        from langchain_core.messages import HumanMessage

        agent = await get_agent()

        thread_id = request.thread_id or f"chat_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=request.question)]},
            config={"configurable": {"thread_id": thread_id}},
        )

        # Extract last AI message
        last_msg = None
        for msg in reversed(result.get("messages", [])):
            msg_type = getattr(msg, "type", None)
            if msg_type == "ai":
                last_msg = msg
                break

        if last_msg is None:
            raise HTTPException(status_code=500, detail="No AI response generated")

        return JSONResponse(
            content={
                "answer": last_msg.content if hasattr(last_msg, "content") else str(last_msg.content),
                "thread_id": thread_id,
                "export_trace_id": result.get("export_trace_id"),
                "llm_calls": result.get("llm_calls", 0),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/test/dataset", response_model=TestDatasetResponse)
async def test_dataset(request: TestDatasetRequest) -> TestDatasetResponse:
    """Run dataset test against the agent."""
    try:
        tester = DatasetTester(dataset_name=request.dataset_name)

        # Load dataset from LangFuse
        items, item_ids = await tester.load_dataset_from_langfuse(request.dataset_name)

        # Run experiments
        raw_results = await tester.run_local_experiment(items, item_ids)

        # Compute statistics
        total = len(raw_results)
        successful = sum(1 for r in raw_results if not r.get("error"))
        failed = total - successful
        rate = f"{(successful / total * 100):.1f}" if total else "0.0"

        return TestDatasetResponse(
            success=True,
            message=f"Dataset test '{request.dataset_name}' completed successfully",
            dataset_name=request.dataset_name,
            total_tests=total,
            successful=successful,
            failed=failed,
            success_rate=rate,
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=raw_results,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
