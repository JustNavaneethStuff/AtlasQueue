from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from atlasqueue.application.services.task_failure_handler import TaskFailureHandler
from atlasqueue.domain.entities.task import Priority, Task
from atlasqueue.domain.value_objects.enums import ExecutorType, TaskStatus


def _queued_task(*, max_retries: int = 3, attempts: int = 0) -> Task:
    task = Task.create(
        name="fail",
        executor_type=ExecutorType.PYTHON,
        payload={},
        priority=Priority(0),
        max_retries=max_retries,
    )
    task.transition_to(TaskStatus.QUEUED)
    task.attempts = attempts
    return task


@pytest.mark.asyncio
async def test_handle_execution_failure_schedules_retry() -> None:
    task_repo = AsyncMock()
    event_repo = AsyncMock()
    queue = AsyncMock()
    handler = TaskFailureHandler(task_repo, event_repo, queue)
    task = _queued_task(max_retries=3, attempts=0)
    task.transition_to(TaskStatus.RUNNING)

    await handler.handle_execution_failure(task, "boom")

    assert task.attempts == 1
    assert task.status == TaskStatus.QUEUED
    queue.enqueue_scheduled.assert_awaited_once()
    task_repo.save.assert_awaited()


@pytest.mark.asyncio
async def test_handle_execution_failure_moves_to_dlq() -> None:
    task_repo = AsyncMock()
    event_repo = AsyncMock()
    queue = AsyncMock()
    handler = TaskFailureHandler(task_repo, event_repo, queue)
    task = _queued_task(max_retries=1, attempts=0)
    task.transition_to(TaskStatus.RUNNING)

    await handler.handle_execution_failure(task, "boom")

    assert task.status == TaskStatus.DEAD_LETTER
    queue.enqueue_dlq.assert_awaited_once()
