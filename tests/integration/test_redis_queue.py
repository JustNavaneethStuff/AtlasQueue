from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from atlasqueue.domain.entities.task import TaskId
from atlasqueue.infrastructure.redis.queue_backend import RedisQueueBackend, create_redis_client
from atlasqueue.shared.config import Settings


@pytest_asyncio.fixture
async def redis_backend():
    settings = Settings(REDIS_URL="redis://localhost:6379/0")
    client = create_redis_client(settings)
    backend = RedisQueueBackend(client, settings)
    try:
        await client.ping()
    except Exception:
        pytest.skip("Redis not available")
    yield backend
    await client.flushdb()
    await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enqueue_dequeue_ready(redis_backend: RedisQueueBackend) -> None:
    task_id = TaskId.generate()
    await redis_backend.enqueue_ready(task_id, priority=0)
    dequeued = await redis_backend.dequeue_ready(timeout=1)
    assert dequeued == task_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduled_tasks(redis_backend: RedisQueueBackend) -> None:
    task_id = TaskId.generate()
    run_at = datetime.now(UTC) - timedelta(seconds=1)
    await redis_backend.enqueue_scheduled(task_id, run_at)
    due = await redis_backend.get_due_scheduled(limit=10)
    assert task_id in due
