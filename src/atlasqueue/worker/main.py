from __future__ import annotations

import asyncio
import socket
import uuid

from atlasqueue.infrastructure.di.container import Container
from atlasqueue.infrastructure.http.webhook_client import WebhookExecutor
from atlasqueue.infrastructure.observability.telemetry import setup_telemetry
from atlasqueue.shared.config import get_settings
from atlasqueue.shared.logging import get_logger, setup_logging
from atlasqueue.worker.executor.python_executor import (
    PythonHandlerExecutor,
    load_tasks_module,
    registry,
)
from atlasqueue.worker.pool import WorkerPool

logger = get_logger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    setup_logging(settings)
    setup_telemetry(settings, "atlasqueue-worker")

    worker_id = settings.worker_id or str(uuid.uuid4())
    hostname = socket.gethostname()
    load_tasks_module(settings.worker_tasks_module)

    container = Container(settings)
    python_executor = PythonHandlerExecutor(registry)
    webhook_executor = WebhookExecutor(settings)

    async with container.session() as session:
        registry_service = await container.worker_registry(session)
        worker = await registry_service.register(hostname, {"worker_id": worker_id})
        worker_id = str(worker.id)

    pool = WorkerPool(
        container=container,
        worker_id=worker_id,
        hostname=hostname,
        concurrency=settings.worker_concurrency,
        python_executor=python_executor,
        webhook_executor=webhook_executor,
        heartbeat_interval=settings.worker_heartbeat_interval,
    )

    logger.info("Starting worker %s with concurrency %d", worker_id, settings.worker_concurrency)
    try:
        await pool.run()
    finally:
        await webhook_executor.aclose()
        await container.close()


def run() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    run()
