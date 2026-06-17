from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from atlasqueue.domain.entities.task import Task, TaskId
from atlasqueue.domain.entities.worker import Worker
from atlasqueue.domain.value_objects.enums import TaskStatus


@dataclass(frozen=True)
class TaskEvent:
    id: UUID
    task_id: TaskId
    event_type: str
    from_status: TaskStatus | None
    to_status: TaskStatus | None
    message: str | None
    metadata: dict[str, Any]
    created_at: datetime


class TaskRepository:
    async def save(self, task: Task) -> Task:
        raise NotImplementedError

    async def get_by_id(self, task_id: TaskId) -> Task | None:
        raise NotImplementedError

    async def get_by_idempotency_key(self, key: str) -> Task | None:
        raise NotImplementedError

    async def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        raise NotImplementedError

    async def count_by_status(self) -> dict[str, int]:
        raise NotImplementedError


class TaskEventRepository:
    async def append(
        self,
        task_id: TaskId,
        event_type: str,
        from_status: TaskStatus | None,
        to_status: TaskStatus | None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskEvent:
        raise NotImplementedError

    async def list_for_task(self, task_id: TaskId) -> list[TaskEvent]:
        raise NotImplementedError


class WorkerRepository:
    async def save(self, worker: Worker) -> Worker:
        raise NotImplementedError

    async def get_by_id(self, worker_id: UUID) -> Worker | None:
        raise NotImplementedError

    async def list_workers(self, *, limit: int = 100) -> list[Worker]:
        raise NotImplementedError

    async def mark_stale_offline(self, stale_seconds: int) -> int:
        raise NotImplementedError


class QueueBackend:
    async def enqueue_ready(self, task_id: TaskId, priority: int) -> None:
        raise NotImplementedError

    async def enqueue_scheduled(self, task_id: TaskId, run_at: datetime) -> None:
        raise NotImplementedError

    async def dequeue_ready(self, timeout: int = 5) -> TaskId | None:
        raise NotImplementedError

    async def remove_scheduled(self, task_id: TaskId) -> None:
        raise NotImplementedError

    async def get_due_scheduled(self, limit: int) -> list[TaskId]:
        raise NotImplementedError

    async def mark_inflight(self, task_id: TaskId, worker_id: str, ttl_seconds: int) -> None:
        raise NotImplementedError

    async def clear_inflight(self, task_id: TaskId) -> None:
        raise NotImplementedError

    async def enqueue_dlq(self, task_id: TaskId) -> None:
        raise NotImplementedError

    async def dequeue_dlq(self) -> TaskId | None:
        raise NotImplementedError

    async def mark_cancelled(self, task_id: TaskId) -> None:
        raise NotImplementedError

    async def is_cancelled(self, task_id: TaskId) -> bool:
        raise NotImplementedError

    async def clear_cancelled(self, task_id: TaskId) -> None:
        raise NotImplementedError

    async def queue_depths(self) -> dict[str, int]:
        raise NotImplementedError

    async def set_worker_heartbeat(self, worker_id: str, metadata: dict[str, str]) -> None:
        raise NotImplementedError

    async def get_active_workers(self) -> list[str]:
        raise NotImplementedError


class LeaderLock:
    async def acquire(self, ttl_seconds: int) -> bool:
        raise NotImplementedError

    async def renew(self, ttl_seconds: int) -> bool:
        raise NotImplementedError

    async def release(self) -> None:
        raise NotImplementedError
