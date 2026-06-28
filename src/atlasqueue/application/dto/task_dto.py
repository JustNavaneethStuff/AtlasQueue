from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BackoffPolicyDTO(BaseModel):
    strategy: Literal["fixed", "exponential"] = "fixed"
    base_delay_seconds: int = Field(default=5, ge=0)
    max_delay_seconds: int = Field(default=300, ge=1)
    multiplier: float = Field(default=2.0, ge=1.0)


class SubmitTaskRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    executor_type: Literal["python", "webhook"] = "python"
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=2, ge=0, le=10)
    scheduled_at: datetime | None = None
    max_retries: int = Field(default=3, ge=0, le=20)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    backoff_policy: BackoffPolicyDTO | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)


class TaskResponse(BaseModel):
    id: str
    name: str
    executor_type: str
    payload: dict[str, Any]
    status: str
    priority: int
    scheduled_at: datetime | None
    attempts: int
    max_retries: int
    timeout_seconds: int
    worker_id: str | None
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime | None
    updated_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    limit: int
    offset: int


class RegisterWorkerRequest(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    metadata: dict[str, str] = Field(default_factory=dict)


class WorkerResponse(BaseModel):
    id: str
    hostname: str
    status: str
    registered_at: datetime
    last_seen_at: datetime
    metadata: dict[str, str]


class TaskEventResponse(BaseModel):
    id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    message: str | None
    metadata: dict[str, Any]
    created_at: datetime


class AdminStatsResponse(BaseModel):
    tasks_by_status: dict[str, int]
    queue_depths: dict[str, int]
    active_workers: int
    workers: list[WorkerResponse]


class HealthResponse(BaseModel):
    status: str
    service: str = "atlasqueue"


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
    request_id: str | None = None
    errors: list[dict[str, Any]] | None = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
