from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlasqueue.application.services.queue_manager import (
    CancellationService,
    InflightReconciler,
    QueueManager,
    SchedulerService,
    WorkerRegistry,
)
from atlasqueue.infrastructure.persistence.database import create_session_factory
from atlasqueue.infrastructure.persistence.repositories import (
    SqlAlchemyTaskEventRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyWorkerRepository,
)
from atlasqueue.infrastructure.redis.queue_backend import (
    RedisLeaderLock,
    RedisQueueBackend,
    create_redis_client,
)
from atlasqueue.shared.config import Settings, get_settings


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.session_factory: async_sessionmaker[AsyncSession] = create_session_factory(self.settings)
        self.redis: redis.Redis[bytes] = create_redis_client(self.settings)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def queue_backend(self) -> RedisQueueBackend:
        return RedisQueueBackend(self.redis, self.settings)

    def leader_lock(self, owner_id: str) -> RedisLeaderLock:
        return RedisLeaderLock(self.redis, owner_id)

    async def queue_manager(self, session: AsyncSession) -> QueueManager:
        return QueueManager(
            SqlAlchemyTaskRepository(session),
            SqlAlchemyTaskEventRepository(session),
            self.queue_backend(),
            self.settings,
        )

    async def cancellation_service(self, session: AsyncSession) -> CancellationService:
        return CancellationService(
            SqlAlchemyTaskRepository(session),
            SqlAlchemyTaskEventRepository(session),
            self.queue_backend(),
        )

    async def scheduler_service(self, session: AsyncSession) -> SchedulerService:
        return SchedulerService(
            SqlAlchemyTaskRepository(session),
            SqlAlchemyTaskEventRepository(session),
            self.queue_backend(),
            self.settings,
        )

    async def worker_registry(self, session: AsyncSession) -> WorkerRegistry:
        return WorkerRegistry(SqlAlchemyWorkerRepository(session), self.queue_backend())

    async def inflight_reconciler(self, session: AsyncSession) -> InflightReconciler:
        return InflightReconciler(
            SqlAlchemyTaskRepository(session),
            SqlAlchemyTaskEventRepository(session),
            self.queue_backend(),
            self.settings,
        )

    async def close(self) -> None:
        await self.redis.close()


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container
