"""FastAPI request/response schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    thread_id: Optional[str] = Field(default=None, description="会话线程ID，用于状态持久化")


class TestDatasetRequest(BaseModel):
    dataset_name: str = Field(..., description="LangFuse 数据集名称")


class EvaluationResult(BaseModel):
    name: str
    value: float
    comment: Optional[str] = None


class TestResult(BaseModel):
    input: str
    output: str
    expected_output: Optional[str] = None
    duration: float
    error: Optional[str] = None
    evaluations: list[EvaluationResult] = []


class TestDatasetResponse(BaseModel):
    success: bool
    message: str
    dataset_name: str
    total_tests: int
    successful: int
    failed: int
    success_rate: str
    timestamp: str
    results: list[TestResult]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    success: bool = False
