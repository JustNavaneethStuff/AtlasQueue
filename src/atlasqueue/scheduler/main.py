from __future__ import annotations

import asyncio
import socket
import uuid

from atlasqueue.infrastructure.di.container import Container
from atlasqueue.infrastructure.observability.telemetry import setup_telemetry
from atlasqueue.shared.config import get_settings
from atlasqueue.shared.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def run_scheduler() -> None:
    settings = get_settings()
    setup_logging(settings)
    setup_telemetry(settings, "atlasqueue-scheduler")

    owner_id = f"{socket.gethostname()}-{uuid.uuid4()}"
    container = Container(settings)
    lock = container.leader_lock(owner_id)

    logger.info("Scheduler starting, owner_id=%s", owner_id)

    try:
        while True:
            acquired = await lock.acquire(settings.scheduler_lock_ttl)
            if acquired:
                try:
                    while await lock.renew(settings.scheduler_lock_ttl):
                        async with container.session() as session:
                            scheduler = await container.scheduler_service(session)
                            processed = await scheduler.process_due_tasks()
                            if processed:
                                logger.info("Released %d scheduled tasks", processed)
                            reconciler = await container.inflight_reconciler(session)
                            requeued = await reconciler.reconcile()
                            if requeued:
                                logger.info("Requeued %d inflight tasks", requeued)
                            manager = await container.queue_manager(session)
                            reconciled = await manager.reconcile_enqueue_failed()
                            if reconciled:
                                logger.info("Reconciled %d enqueue_failed tasks", reconciled)
                        await asyncio.sleep(settings.scheduler_tick_interval)
                finally:
                    await lock.release()
            else:
                await asyncio.sleep(settings.scheduler_tick_interval)
    finally:
        await container.close()


def run() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    run()
