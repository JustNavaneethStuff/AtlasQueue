from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from atlasqueue.application.dto.task_dto import SubmitTaskRequest
from atlasqueue.domain.entities.task import BackoffPolicy, Priority, Task, TaskId
from atlasqueue.domain.entities.worker import Worker
from atlasqueue.domain.exceptions import (
    EnqueueFailedError,
    InvalidTaskStateError,
    PayloadTooLargeError,
    TaskNotFoundError,
)
from atlasqueue.domain.ports.repositories import (
    QueueBackend,
    TaskEvent,
    TaskEventRepository,
    TaskRepository,
    WorkerRepository,
)
from atlasqueue.domain.value_objects.enums import ExecutorType, TaskStatus
from atlasqueue.infrastructure.observability.metrics import TASKS_CANCELLED, TASKS_SUBMITTED
from atlasqueue.shared.config import Settings
from atlasqueue.shared.logging import get_logger

logger = get_logger(__name__)


class QueueManager:
    def __init__(
        self,
        task_repo: TaskRepository,
        event_repo: TaskEventRepository,
        queue: QueueBackend,
        settings: Settings,
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._queue = queue
        self._settings = settings

    async def submit(self, request: SubmitTaskRequest) -> Task:
        if request.idempotency_key:
            existing = await self._task_repo.get_by_idempotency_key(request.idempotency_key)
            if existing:
                return existing

        payload_size = len(str(request.payload).encode())
        if payload_size > self._settings.max_payload_bytes:
            raise PayloadTooLargeError(self._settings.max_payload_bytes)

        backoff = None
        if request.backoff_policy:
            backoff = BackoffPolicy(
                strategy=request.backoff_policy.strategy,
                base_delay_seconds=request.backoff_policy.base_delay_seconds,
                max_delay_seconds=request.backoff_policy.max_delay_seconds,
                multiplier=request.backoff_policy.multiplier,
            )

        task = Task.create(
            name=request.name,
            executor_type=ExecutorType(request.executor_type),
            payload=request.payload,
            priority=Priority(request.priority),
            max_retries=request.max_retries,
            scheduled_at=request.scheduled_at,
            timeout_seconds=request.timeout_seconds,
            backoff_policy=backoff,
            idempotency_key=request.idempotency_key,
        )

        await self._task_repo.save(task)
        await self._event_repo.append(
            task.id,
            "task.submitted",
            None,
            task.status,
            metadata={"name": task.name},
        )

        try:
            await self._enqueue(task)
        except Exception as exc:
            logger.exception("Failed to enqueue task %s", task.id)
            from_status = task.status
            task.transition_to(TaskStatus.ENQUEUE_FAILED)
            await self._task_repo.save(task)
            await self._event_repo.append(
                task.id,
                "task.enqueue_failed",
                from_status,
                task.status,
                message=str(exc),
            )
            raise EnqueueFailedError(str(exc)) from exc

        TASKS_SUBMITTED.labels(task_name=task.name, executor_type=task.executor_type.value).inc()
        return task

    async def _enqueue(self, task: Task) -> None:
        now = datetime.now(UTC)
        from_status = task.status
        if task.scheduled_at and task.scheduled_at > now:
            await self._queue.enqueue_scheduled(task.id, task.scheduled_at)
            task.transition_to(TaskStatus.SCHEDULED)
        else:
            await self._queue.enqueue_ready(task.id, task.priority.value)
            task.transition_to(TaskStatus.QUEUED)
        await self._task_repo.save(task)
        await self._event_repo.append(
            task.id,
            "task.enqueued",
            from_status,
            task.status,
        )

    async def get_task(self, task_id: TaskId) -> Task | None:
        return await self._task_repo.get_by_id(task_id)

    async def get_task_or_raise(self, task_id: TaskId) -> Task:
        task = await self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(str(task_id))
        return task

    async def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        name: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        return await self._task_repo.list_tasks(
            status=status,
            name=name,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    async def count_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        name: str | None = None,
    ) -> int:
        return await self._task_repo.count_tasks(status=status, name=name)

    async def get_task_events(self, task_id: TaskId) -> list[TaskEvent]:
        await self.get_task_or_raise(task_id)
        return await self._event_repo.list_for_task(task_id)

    async def get_admin_stats(self) -> dict[str, Any]:
        tasks_by_status = await self._task_repo.count_by_status()
        depths = await self._queue.queue_depths()
        active_redis = await self._queue.get_active_workers()
        return {
            "tasks_by_status": tasks_by_status,
            "queue_depths": depths,
            "active_workers": len(active_redis),
        }

    async def retry_task(self, task_id: TaskId) -> Task:
        task = await self.get_task_or_raise(task_id)
        if task.status not in (TaskStatus.DEAD_LETTER, TaskStatus.FAILED):
            raise InvalidTaskStateError(f"Task {task_id} is not in a retriable state: {task.status}")
        from_status = task.status
        task.error = None
        task.attempts = 0
        task.worker_id = None
        task.started_at = None
        task.finished_at = None
        task.transition_to(TaskStatus.QUEUED)
        await self._queue.enqueue_ready(task.id, task.priority.value)
        await self._task_repo.save(task)
        await self._event_repo.append(task.id, "task.retried", from_status, task.status)
        from atlasqueue.infrastructure.observability.metrics import TASKS_RETRIED

        TASKS_RETRIED.inc()
        return task

    async def reconcile_enqueue_failed(self, batch_size: int = 50) -> int:
        tasks = await self._task_repo.list_tasks(status=TaskStatus.ENQUEUE_FAILED, limit=batch_size)
        count = 0
        for task in tasks:
            try:
                await self._enqueue(task)
                count += 1
            except Exception:
                logger.exception("Reconcile failed for task %s", task.id)
        return count


class CancellationService:
    def __init__(
        self,
        task_repo: TaskRepository,
        event_repo: TaskEventRepository,
        queue: QueueBackend,
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._queue = queue

    async def cancel(self, task_id: TaskId) -> Task:
        task = await self._task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(str(task_id))
        if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.DEAD_LETTER):
            raise InvalidTaskStateError(f"Task {task_id} cannot be cancelled in status {task.status}")

        from_status = task.status
        await self._queue.mark_cancelled(task_id)
        if from_status == TaskStatus.SCHEDULED:
            await self._queue.remove_scheduled(task_id)
        task.transition_to(TaskStatus.CANCELLED)
        task.finished_at = datetime.now(UTC)
        await self._task_repo.save(task)
        await self._event_repo.append(task.id, "task.cancelled", from_status, task.status)
        TASKS_CANCELLED.inc()
        return task


class SchedulerService:
    def __init__(
        self,
        task_repo: TaskRepository,
        event_repo: TaskEventRepository,
        queue: QueueBackend,
        settings: Settings,
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._queue = queue
        self._settings = settings

    async def process_due_tasks(self) -> int:
        due_ids = await self._queue.claim_due_scheduled(self._settings.scheduler_batch_size)
        processed = 0
        for task_id in due_ids:
            task = await self._task_repo.get_by_id(task_id)
            if not task or task.status != TaskStatus.SCHEDULED:
                continue
            from_status = task.status
            await self._queue.enqueue_ready(task.id, task.priority.value)
            task.transition_to(TaskStatus.QUEUED)
            await self._task_repo.save(task)
            await self._event_repo.append(task.id, "task.scheduled_release", from_status, task.status)
            processed += 1
        return processed


class WorkerRegistry:
    def __init__(
        self,
        worker_repo: WorkerRepository,
        queue: QueueBackend,
    ) -> None:
        self._worker_repo = worker_repo
        self._queue = queue

    async def register(self, hostname: str, metadata: dict[str, str] | None = None) -> Worker:
        worker = Worker.create(hostname, metadata)
        await self._worker_repo.save(worker)
        await self._queue.set_worker_heartbeat(str(worker.id), {"hostname": hostname})
        return worker

    async def heartbeat(self, worker_id: str, hostname: str) -> None:
        worker = await self._worker_repo.get_by_id(UUID(worker_id))
        if worker:
            worker.heartbeat()
            await self._worker_repo.save(worker)
        await self._queue.set_worker_heartbeat(worker_id, {"hostname": hostname})

    async def list_workers(self, limit: int = 100) -> list[Worker]:
        return await self._worker_repo.list_workers(limit=limit)

    async def mark_stale(self, stale_seconds: int = 60) -> int:
        return await self._worker_repo.mark_stale_offline(stale_seconds)


class InflightReconciler:
    def __init__(
        self,
        task_repo: TaskRepository,
        event_repo: TaskEventRepository,
        queue: QueueBackend,
        settings: Settings,
    ) -> None:
        from atlasqueue.application.services.task_failure_handler import TaskFailureHandler

        self._task_repo = task_repo
        self._settings = settings
        self._failure_handler = TaskFailureHandler(task_repo, event_repo, queue)
        self._queue = queue

    async def reconcile(self) -> int:
        from datetime import timedelta

        requeued = 0
        inflight_ids = await self._queue.get_inflight_task_ids()
        for task_id in inflight_ids:
            task = await self._task_repo.get_by_id(task_id)
            if not task or task.status != TaskStatus.RUNNING:
                await self._queue.clear_inflight(task_id)
                continue
            if task.started_at and datetime.now(UTC) - task.started_at > timedelta(seconds=task.timeout_seconds + 30):
                await self._failure_handler.handle_timeout(task)
                requeued += 1
        return requeued
