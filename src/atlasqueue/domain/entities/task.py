from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from atlasqueue.domain.value_objects.enums import ExecutorType, TaskStatus


@dataclass(frozen=True)
class TaskId:
    value: UUID

    @classmethod
    def generate(cls) -> TaskId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> TaskId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Priority:
    """Lower number = higher priority (0 is highest)."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            msg = "Priority must be non-negative"
            raise ValueError(msg)

    @classmethod
    def critical(cls) -> Priority:
        return cls(0)

    @classmethod
    def normal(cls) -> Priority:
        return cls(2)


@dataclass
class BackoffPolicy:
    strategy: str = "fixed"
    base_delay_seconds: int = 5
    max_delay_seconds: int = 300
    multiplier: float = 2.0

    def delay_for_attempt(self, attempt: int) -> int:
        if self.strategy == "exponential":
            delay = int(self.base_delay_seconds * (self.multiplier ** max(attempt - 1, 0)))
            return min(delay, self.max_delay_seconds)
        return self.base_delay_seconds


@dataclass
class Task:
    id: TaskId
    name: str
    executor_type: ExecutorType
    payload: dict[str, Any]
    status: TaskStatus
    priority: Priority
    max_retries: int
    attempts: int = 0
    scheduled_at: datetime | None = None
    timeout_seconds: int = 300
    backoff_policy: BackoffPolicy | None = None
    worker_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    idempotency_key: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.backoff_policy is None:
            self.backoff_policy = BackoffPolicy()

    @classmethod
    def create(
        cls,
        *,
        name: str,
        executor_type: ExecutorType,
        payload: dict[str, Any],
        priority: Priority,
        max_retries: int,
        scheduled_at: datetime | None = None,
        timeout_seconds: int = 300,
        backoff_policy: BackoffPolicy | None = None,
        idempotency_key: str | None = None,
    ) -> Task:
        now = datetime.now(UTC)
        status = TaskStatus.SCHEDULED if scheduled_at and scheduled_at > now else TaskStatus.PENDING
        return cls(
            id=TaskId.generate(),
            name=name,
            executor_type=executor_type,
            payload=payload,
            status=status,
            priority=priority,
            max_retries=max_retries,
            scheduled_at=scheduled_at,
            timeout_seconds=timeout_seconds,
            backoff_policy=backoff_policy or BackoffPolicy(),
            idempotency_key=idempotency_key,
            created_at=now,
            updated_at=now,
        )

    def can_retry(self) -> bool:
        return self.attempts < self.max_retries

    def retry_delay_seconds(self) -> int:
        policy = self.backoff_policy or BackoffPolicy()
        return policy.delay_for_attempt(self.attempts)

    def transition_to(self, status: TaskStatus) -> None:
        allowed: dict[TaskStatus, set[TaskStatus]] = {
            TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.ENQUEUE_FAILED, TaskStatus.CANCELLED},
            TaskStatus.SCHEDULED: {
                TaskStatus.QUEUED,
                TaskStatus.CANCELLED,
                TaskStatus.ENQUEUE_FAILED,
            },
            TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
                TaskStatus.QUEUED,
                TaskStatus.DEAD_LETTER,
            },
            TaskStatus.FAILED: {TaskStatus.QUEUED, TaskStatus.DEAD_LETTER},
            TaskStatus.ENQUEUE_FAILED: {TaskStatus.QUEUED, TaskStatus.SCHEDULED},
            TaskStatus.DEAD_LETTER: {TaskStatus.QUEUED},
            TaskStatus.COMPLETED: set(),
            TaskStatus.CANCELLED: set(),
        }
        if status not in allowed.get(self.status, set()):
            msg = f"Invalid transition from {self.status} to {status}"
            raise ValueError(msg)
        self.status = status
        self.updated_at = datetime.now(UTC)
