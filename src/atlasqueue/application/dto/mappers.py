from __future__ import annotations

from atlasqueue.application.dto.task_dto import TaskResponse
from atlasqueue.domain.entities.task import Task


def task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=str(task.id),
        name=task.name,
        executor_type=task.executor_type.value,
        payload=task.payload,
        status=task.status.value,
        priority=task.priority.value,
        scheduled_at=task.scheduled_at,
        attempts=task.attempts,
        max_retries=task.max_retries,
        timeout_seconds=task.timeout_seconds,
        worker_id=task.worker_id,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )
