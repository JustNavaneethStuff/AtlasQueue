from __future__ import annotations

import asyncio
import importlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from atlasqueue.application.services.task_failure_handler import TaskFailureHandler
from atlasqueue.domain.entities.task import Task
from atlasqueue.domain.ports.repositories import QueueBackend, TaskEventRepository, TaskRepository
from atlasqueue.domain.value_objects.enums import ExecutorType, TaskStatus
from atlasqueue.infrastructure.http.webhook_client import WebhookExecutor
from atlasqueue.infrastructure.observability.metrics import TASK_DURATION, TASKS_COMPLETED
from atlasqueue.shared.logging import get_logger

logger = get_logger(__name__)

TaskHandler = Callable[..., Any]
AsyncTaskHandler = Callable[..., Awaitable[Any]]


class TaskRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, TaskHandler | AsyncTaskHandler] = {}

    def register(self, name: str, handler: TaskHandler | AsyncTaskHandler) -> None:
        self._handlers[name] = handler

    def get(self, name: str) -> TaskHandler | AsyncTaskHandler | None:
        return self._handlers.get(name)

    @property
    def names(self) -> list[str]:
        return list(self._handlers.keys())


registry = TaskRegistry()


def task(name: str | None = None) -> Callable[[TaskHandler | AsyncTaskHandler], TaskHandler | AsyncTaskHandler]:
    def decorator(fn: TaskHandler | AsyncTaskHandler) -> TaskHandler | AsyncTaskHandler:
        task_name = name or fn.__name__
        registry.register(task_name, fn)
        return fn

    return decorator


class PythonHandlerExecutor:
    def __init__(self, task_registry: TaskRegistry) -> None:
        self._registry = task_registry

    async def execute(self, task: Task) -> dict[str, Any]:
        handler = self._registry.get(task.name)
        if not handler:
            msg = f"No handler registered for task '{task.name}'"
            raise ValueError(msg)
        payload = task.payload
        if asyncio.iscoroutinefunction(handler):
            result = await handler(**payload) if payload else await handler()
        else:
            result = await asyncio.to_thread(handler, **payload) if payload else await asyncio.to_thread(handler)
        if isinstance(result, dict):
            return result
        return {"result": result}


def load_tasks_module(module_path: str) -> None:
    importlib.import_module(module_path)
    logger.info("Loaded task handlers from %s: %s", module_path, registry.names)


class TaskExecutorService:
    def __init__(
        self,
        task_repo: TaskRepository,
        event_repo: TaskEventRepository,
        queue: QueueBackend,
        python_executor: PythonHandlerExecutor,
        webhook_executor: WebhookExecutor,
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._queue = queue
        self._python = python_executor
        self._webhook = webhook_executor
        self._failure_handler = TaskFailureHandler(task_repo, event_repo, queue)

    async def execute_task(self, task: Task, worker_id: str) -> None:
        if await self._queue.is_cancelled(task.id):
            from_status = task.status
            task.transition_to(TaskStatus.CANCELLED)
            task.finished_at = datetime.now(UTC)
            await self._task_repo.save(task)
            await self._event_repo.append(task.id, "task.cancelled", from_status, task.status)
            await self._queue.clear_cancelled(task.id)
            return

        from_status = task.status
        task.transition_to(TaskStatus.RUNNING)
        task.worker_id = worker_id
        task.started_at = datetime.now(UTC)
        await self._task_repo.save(task)
        await self._event_repo.append(task.id, "task.started", from_status, task.status)
        await self._queue.mark_inflight(task.id, worker_id, task.timeout_seconds + 60)

        start = datetime.now(UTC)
        try:
            if task.executor_type == ExecutorType.WEBHOOK:
                result = await asyncio.wait_for(
                    self._webhook.execute(task),
                    timeout=task.timeout_seconds,
                )
            else:
                result = await asyncio.wait_for(
                    self._python.execute(task),
                    timeout=task.timeout_seconds,
                )
            from_status = task.status
            task.transition_to(TaskStatus.COMPLETED)
            task.result = result
            task.finished_at = datetime.now(UTC)
            task.error = None
            await self._task_repo.save(task)
            await self._event_repo.append(task.id, "task.completed", from_status, task.status)
            TASKS_COMPLETED.labels(task_name=task.name, status="completed").inc()
        except Exception as exc:
            logger.exception("Task %s failed: %s", task.id, exc)
            await self._failure_handler.handle_execution_failure(task, str(exc))
        finally:
            await self._queue.clear_inflight(task.id)
            duration = (datetime.now(UTC) - start).total_seconds()
            TASK_DURATION.labels(task_name=task.name).observe(duration)
