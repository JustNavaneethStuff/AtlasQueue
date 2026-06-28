from __future__ import annotations

from datetime import UTC, datetime, timedelta

from atlasqueue.domain.entities.task import Task
from atlasqueue.domain.ports.repositories import QueueBackend, TaskEventRepository, TaskRepository
from atlasqueue.domain.value_objects.enums import TaskStatus
from atlasqueue.infrastructure.observability.metrics import TASKS_COMPLETED
from atlasqueue.shared.logging import get_logger

logger = get_logger(__name__)


class TaskFailureHandler:
    """Centralizes retry, DLQ, and timeout failure handling."""

    def __init__(
        self,
        task_repo: TaskRepository,
        event_repo: TaskEventRepository,
        queue: QueueBackend,
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._queue = queue

    async def handle_execution_failure(self, task: Task, error: str) -> None:
        from_status = task.status
        task.attempts += 1
        task.error = error
        if task.can_retry():
            await self._schedule_retry(task, from_status, error, event_type="task.retry_scheduled")
            TASKS_COMPLETED.labels(task_name=task.name, status="retry").inc()
            return

        await self._move_to_dead_letter(task, from_status, error, event_type="task.dead_letter")
        TASKS_COMPLETED.labels(task_name=task.name, status="dead_letter").inc()

    async def handle_timeout(self, task: Task) -> bool:
        """Requeue or DLQ a running task that exceeded its timeout. Returns True if handled."""
        from_status = task.status
        task.attempts += 1
        task.worker_id = None
        task.started_at = None
        if task.can_retry():
            await self._schedule_retry(
                task,
                from_status,
                "Exceeded execution timeout",
                event_type="task.requeued_timeout",
                message_template="Requeued after timeout, delay={delay}s",
            )
        else:
            await self._move_to_dead_letter(
                task,
                from_status,
                "Exceeded max retries after timeout",
                event_type="task.dead_letter",
            )
        await self._task_repo.save(task)
        await self._queue.clear_inflight(task.id)
        return True

    async def _schedule_retry(
        self,
        task: Task,
        from_status: TaskStatus,
        error: str,
        *,
        event_type: str,
        message_template: str | None = None,
    ) -> None:
        task.transition_to(TaskStatus.QUEUED)
        delay = task.retry_delay_seconds()
        run_at = datetime.now(UTC) + timedelta(seconds=delay)
        await self._queue.enqueue_scheduled(task.id, run_at)
        await self._task_repo.save(task)
        message = (
            message_template.format(delay=delay)
            if message_template
            else f"Retry in {delay}s (attempt {task.attempts}/{task.max_retries}): {error}"
        )
        await self._event_repo.append(task.id, event_type, from_status, task.status, message=message)

    async def _move_to_dead_letter(
        self,
        task: Task,
        from_status: TaskStatus,
        error: str,
        *,
        event_type: str,
    ) -> None:
        task.transition_to(TaskStatus.DEAD_LETTER)
        task.finished_at = datetime.now(UTC)
        await self._queue.enqueue_dlq(task.id)
        await self._task_repo.save(task)
        await self._event_repo.append(task.id, event_type, from_status, task.status, message=error)
