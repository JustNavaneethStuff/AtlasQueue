from __future__ import annotations

from atlasqueue.application.dto.task_dto import TaskEventResponse, TaskResponse, WorkerResponse
from atlasqueue.domain.entities.task import Task
from atlasqueue.domain.entities.worker import Worker
from atlasqueue.domain.ports.repositories import TaskEvent


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


def worker_to_response(worker: Worker) -> WorkerResponse:
    return WorkerResponse(
        id=str(worker.id),
        hostname=worker.hostname,
        status=worker.status.value,
        registered_at=worker.registered_at,
        last_seen_at=worker.last_seen_at,
        metadata=worker.metadata,
    )


def task_event_to_response(event: TaskEvent) -> TaskEventResponse:
    return TaskEventResponse(
        id=str(event.id),
        event_type=event.event_type,
        from_status=event.from_status.value if event.from_status else None,
        to_status=event.to_status.value if event.to_status else None,
        message=event.message,
        metadata=event.metadata,
        created_at=event.created_at,
    )
