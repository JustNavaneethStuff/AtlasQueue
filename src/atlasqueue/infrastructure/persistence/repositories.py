from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from atlasqueue.domain.entities.task import BackoffPolicy, Priority, Task, TaskId
from atlasqueue.domain.entities.worker import Worker
from atlasqueue.domain.ports.repositories import (
    TaskEvent,
    TaskEventRepository,
    TaskRepository,
    WorkerRepository,
)
from atlasqueue.domain.value_objects.enums import ExecutorType, TaskStatus, WorkerStatus
from atlasqueue.infrastructure.persistence.models import TaskEventModel, TaskModel, WorkerModel


def _to_domain_task(model: TaskModel) -> Task:
    backoff_data = model.backoff_policy or {}
    return Task(
        id=TaskId(model.id),
        name=model.name,
        executor_type=ExecutorType(model.executor_type),
        payload=model.payload,
        status=TaskStatus(model.status),
        priority=Priority(model.priority),
        max_retries=model.max_retries,
        attempts=model.attempts,
        scheduled_at=model.scheduled_at,
        timeout_seconds=model.timeout_seconds,
        backoff_policy=BackoffPolicy(
            strategy=backoff_data.get("strategy", "fixed"),
            base_delay_seconds=backoff_data.get("base_delay_seconds", 5),
            max_delay_seconds=backoff_data.get("max_delay_seconds", 300),
            multiplier=backoff_data.get("multiplier", 2.0),
        ),
        worker_id=model.worker_id,
        result=model.result,
        error=model.error,
        idempotency_key=model.idempotency_key,
        created_at=model.created_at,
        updated_at=model.updated_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def _to_model_task(task: Task) -> TaskModel:
    policy = task.backoff_policy or BackoffPolicy()
    return TaskModel(
        id=task.id.value,
        name=task.name,
        executor_type=task.executor_type.value,
        payload=task.payload,
        status=task.status.value,
        priority=task.priority.value,
        scheduled_at=task.scheduled_at,
        attempts=task.attempts,
        max_retries=task.max_retries,
        timeout_seconds=task.timeout_seconds,
        backoff_policy={
            "strategy": policy.strategy,
            "base_delay_seconds": policy.base_delay_seconds,
            "max_delay_seconds": policy.max_delay_seconds,
            "multiplier": policy.multiplier,
        },
        worker_id=task.worker_id,
        result=task.result,
        error=task.error,
        idempotency_key=task.idempotency_key,
        created_at=task.created_at or datetime.now(UTC),
        updated_at=task.updated_at or datetime.now(UTC),
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


class SqlAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, task: Task) -> Task:
        existing = await self._session.get(TaskModel, task.id.value)
        if existing is None:
            self._session.add(_to_model_task(task))
        else:
            existing.name = task.name
            existing.executor_type = task.executor_type.value
            existing.payload = task.payload
            existing.status = task.status.value
            existing.priority = task.priority.value
            existing.scheduled_at = task.scheduled_at
            existing.attempts = task.attempts
            existing.max_retries = task.max_retries
            existing.timeout_seconds = task.timeout_seconds
            policy = task.backoff_policy or BackoffPolicy()
            existing.backoff_policy = {
                "strategy": policy.strategy,
                "base_delay_seconds": policy.base_delay_seconds,
                "max_delay_seconds": policy.max_delay_seconds,
                "multiplier": policy.multiplier,
            }
            existing.worker_id = task.worker_id
            existing.result = task.result
            existing.error = task.error
            existing.updated_at = task.updated_at or datetime.now(UTC)
            existing.started_at = task.started_at
            existing.finished_at = task.finished_at
        await self._session.flush()
        return task

    async def get_by_id(self, task_id: TaskId) -> Task | None:
        model = await self._session.get(TaskModel, task_id.value)
        return _to_domain_task(model) if model else None

    async def get_by_idempotency_key(self, key: str) -> Task | None:
        result = await self._session.execute(select(TaskModel).where(TaskModel.idempotency_key == key))
        model = result.scalar_one_or_none()
        return _to_domain_task(model) if model else None

    async def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        query = select(TaskModel).order_by(TaskModel.created_at.desc()).limit(limit).offset(offset)
        if status:
            query = query.where(TaskModel.status == status.value)
        result = await self._session.execute(query)
        return [_to_domain_task(m) for m in result.scalars().all()]

    async def count_by_status(self) -> dict[str, int]:
        result = await self._session.execute(select(TaskModel.status, func.count()).group_by(TaskModel.status))
        return {status: count for status, count in result.all()}


class SqlAlchemyTaskEventRepository(TaskEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        task_id: TaskId,
        event_type: str,
        from_status: TaskStatus | None,
        to_status: TaskStatus | None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskEvent:
        model = TaskEventModel(
            id=uuid4(),
            task_id=task_id.value,
            event_type=event_type,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value if to_status else None,
            message=message,
            event_metadata=metadata or {},
        )
        self._session.add(model)
        await self._session.flush()
        return TaskEvent(
            id=model.id,
            task_id=task_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            message=message,
            metadata=metadata or {},
            created_at=model.created_at,
        )

    async def list_for_task(self, task_id: TaskId) -> list[TaskEvent]:
        result = await self._session.execute(
            select(TaskEventModel)
            .where(TaskEventModel.task_id == task_id.value)
            .order_by(TaskEventModel.created_at.asc())
        )
        events: list[TaskEvent] = []
        for model in result.scalars().all():
            events.append(
                TaskEvent(
                    id=model.id,
                    task_id=task_id,
                    event_type=model.event_type,
                    from_status=TaskStatus(model.from_status) if model.from_status else None,
                    to_status=TaskStatus(model.to_status) if model.to_status else None,
                    message=model.message,
                    metadata=model.event_metadata,
                    created_at=model.created_at,
                )
            )
        return events


class SqlAlchemyWorkerRepository(WorkerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, worker: Worker) -> Worker:
        existing = await self._session.get(WorkerModel, worker.id)
        if existing is None:
            self._session.add(
                WorkerModel(
                    id=worker.id,
                    hostname=worker.hostname,
                    status=worker.status.value,
                    registered_at=worker.registered_at,
                    last_seen_at=worker.last_seen_at,
                    worker_metadata=worker.metadata,
                )
            )
        else:
            existing.hostname = worker.hostname
            existing.status = worker.status.value
            existing.last_seen_at = worker.last_seen_at
            existing.worker_metadata = worker.metadata
        await self._session.flush()
        return worker

    async def get_by_id(self, worker_id: UUID) -> Worker | None:
        model = await self._session.get(WorkerModel, worker_id)
        if not model:
            return None
        return Worker(
            id=model.id,
            hostname=model.hostname,
            status=WorkerStatus(model.status),
            registered_at=model.registered_at,
            last_seen_at=model.last_seen_at,
            metadata=model.worker_metadata,
        )

    async def list_workers(self, *, limit: int = 100) -> list[Worker]:
        result = await self._session.execute(select(WorkerModel).order_by(WorkerModel.last_seen_at.desc()).limit(limit))
        workers: list[Worker] = []
        for model in result.scalars().all():
            workers.append(
                Worker(
                    id=model.id,
                    hostname=model.hostname,
                    status=WorkerStatus(model.status),
                    registered_at=model.registered_at,
                    last_seen_at=model.last_seen_at,
                    metadata=model.worker_metadata,
                )
            )
        return workers

    async def mark_stale_offline(self, stale_seconds: int) -> int:
        cutoff = datetime.now(UTC)
        from datetime import timedelta

        threshold = cutoff - timedelta(seconds=stale_seconds)
        result = await self._session.execute(
            update(WorkerModel)
            .where(
                WorkerModel.last_seen_at < threshold,
                WorkerModel.status != WorkerStatus.OFFLINE.value,
            )
            .values(status=WorkerStatus.OFFLINE.value)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
