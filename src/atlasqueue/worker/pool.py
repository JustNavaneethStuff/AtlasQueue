from __future__ import annotations

import asyncio

from atlasqueue.domain.entities.task import TaskId
from atlasqueue.domain.value_objects.enums import TaskStatus
from atlasqueue.infrastructure.di.container import Container
from atlasqueue.shared.logging import get_logger

logger = get_logger(__name__)


class WorkerPool:
    def __init__(
        self,
        container: Container,
        worker_id: str,
        hostname: str,
        concurrency: int,
        heartbeat_interval: int = 10,
    ) -> None:
        self._container = container
        self._worker_id = worker_id
        self._hostname = hostname
        self._concurrency = concurrency
        self._heartbeat_interval = heartbeat_interval
        self._semaphore = asyncio.Semaphore(concurrency)
        self._running = True

    async def run(self) -> None:
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        workers = [asyncio.create_task(self._consume_loop()) for _ in range(self._concurrency)]
        try:
            await asyncio.gather(*workers)
        finally:
            self._running = False
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                async with self._container.session() as session:
                    registry = await self._container.worker_registry(session)
                    await registry.heartbeat(self._worker_id, self._hostname)
            except Exception:
                logger.exception("Heartbeat failed")
            await asyncio.sleep(self._heartbeat_interval)

    async def _consume_loop(self) -> None:
        import redis.exceptions

        queue = self._container.queue_backend()
        while self._running:
            try:
                task_id = await queue.dequeue_ready(timeout=5)
            except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError):
                logger.warning("Redis dequeue timeout, retrying")
                await asyncio.sleep(1)
                continue
            if not task_id:
                continue
            await self._semaphore.acquire()
            asyncio.create_task(self._process_task(task_id))

    async def _process_task(self, task_id: TaskId) -> None:
        try:
            async with self._container.session() as session:
                task_repo = await self._container.queue_manager(session)
                task = await task_repo.get_task(task_id)
                if not task:
                    logger.warning("Task %s not found in database", task_id)
                    return
                if task.status != TaskStatus.QUEUED:
                    logger.warning("Task %s in unexpected status %s", task_id, task.status)
                    return
                executor = await self._container.task_executor_service(session)
                await executor.execute_task(task, self._worker_id)
        except Exception:
            logger.exception("Failed processing task %s", task_id)
        finally:
            self._semaphore.release()
