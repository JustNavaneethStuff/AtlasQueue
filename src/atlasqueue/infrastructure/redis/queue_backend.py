from __future__ import annotations

from datetime import UTC, datetime

import redis.asyncio as redis

from atlasqueue.domain.entities.task import TaskId
from atlasqueue.domain.ports.repositories import LeaderLock, QueueBackend
from atlasqueue.shared.config import Settings

READY_PREFIX = "queue:ready:"
SCHEDULED_KEY = "queue:scheduled"
INFLIGHT_PREFIX = "queue:inflight:"
DLQ_KEY = "queue:dlq"
CANCEL_KEY = "cancel:pending"
WORKER_PREFIX = "workers:"
LEADER_LOCK_KEY = "lock:scheduler"


class RedisQueueBackend(QueueBackend):
    def __init__(self, client: redis.Redis[bytes], settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _ready_key(self, priority: int) -> str:
        return f"{READY_PREFIX}{priority}"

    def _ready_keys(self) -> list[str]:
        return [self._ready_key(p) for p in range(self._settings.priority_levels)]

    async def enqueue_ready(self, task_id: TaskId, priority: int) -> None:
        clamped = min(priority, self._settings.priority_levels - 1)
        await self._client.lpush(self._ready_key(clamped), str(task_id))

    async def enqueue_scheduled(self, task_id: TaskId, run_at: datetime) -> None:
        score = run_at.timestamp()
        await self._client.zadd(SCHEDULED_KEY, {str(task_id): score})

    async def dequeue_ready(self, timeout: int = 5) -> TaskId | None:
        result = await self._client.brpop(self._ready_keys(), timeout=timeout)
        if not result:
            return None
        _, task_id_str = result
        return TaskId.from_string(task_id_str.decode() if isinstance(task_id_str, bytes) else task_id_str)

    async def remove_scheduled(self, task_id: TaskId) -> None:
        await self._client.zrem(SCHEDULED_KEY, str(task_id))

    async def get_due_scheduled(self, limit: int) -> list[TaskId]:
        now = datetime.now(UTC).timestamp()
        raw = await self._client.zrangebyscore(SCHEDULED_KEY, 0, now, start=0, num=limit)
        return [TaskId.from_string(item.decode() if isinstance(item, bytes) else item) for item in raw]

    async def mark_inflight(self, task_id: TaskId, worker_id: str, ttl_seconds: int) -> None:
        key = f"{INFLIGHT_PREFIX}{task_id}"
        await self._client.hset(key, mapping={"worker_id": worker_id, "started_at": datetime.now(UTC).isoformat()})
        await self._client.expire(key, ttl_seconds)

    async def clear_inflight(self, task_id: TaskId) -> None:
        await self._client.delete(f"{INFLIGHT_PREFIX}{task_id}")

    async def enqueue_dlq(self, task_id: TaskId) -> None:
        await self._client.lpush(DLQ_KEY, str(task_id))

    async def dequeue_dlq(self) -> TaskId | None:
        result = await self._client.rpop(DLQ_KEY)
        if not result:
            return None
        task_id_str = result.decode() if isinstance(result, bytes) else result
        return TaskId.from_string(task_id_str)

    async def mark_cancelled(self, task_id: TaskId) -> None:
        await self._client.sadd(CANCEL_KEY, str(task_id))

    async def is_cancelled(self, task_id: TaskId) -> bool:
        return bool(await self._client.sismember(CANCEL_KEY, str(task_id)))

    async def clear_cancelled(self, task_id: TaskId) -> None:
        await self._client.srem(CANCEL_KEY, str(task_id))

    async def queue_depths(self) -> dict[str, int]:
        depths: dict[str, int] = {}
        for p in range(self._settings.priority_levels):
            depths[f"ready_{p}"] = await self._client.llen(self._ready_key(p))
        depths["scheduled"] = await self._client.zcard(SCHEDULED_KEY)
        depths["dlq"] = await self._client.llen(DLQ_KEY)
        return depths

    async def set_worker_heartbeat(self, worker_id: str, metadata: dict[str, str]) -> None:
        key = f"{WORKER_PREFIX}{worker_id}"
        mapping: dict[str, str] = {"last_seen": datetime.now(UTC).isoformat(), **metadata}
        await self._client.hset(key, mapping=mapping)  # type: ignore[arg-type]
        await self._client.expire(key, self._settings.worker_heartbeat_interval * 3)

    async def get_active_workers(self) -> list[str]:
        keys = await self._client.keys(f"{WORKER_PREFIX}*")
        worker_ids: list[str] = []
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            worker_ids.append(key_str.replace(WORKER_PREFIX, ""))
        return worker_ids

    async def get_inflight_task_ids(self) -> list[TaskId]:
        keys = await self._client.keys(f"{INFLIGHT_PREFIX}*")
        ids: list[TaskId] = []
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            task_id_str = key_str.replace(INFLIGHT_PREFIX, "")
            ids.append(TaskId.from_string(task_id_str))
        return ids


class RedisLeaderLock(LeaderLock):
    def __init__(self, client: redis.Redis[bytes], owner_id: str) -> None:
        self._client = client
        self._owner_id = owner_id

    async def acquire(self, ttl_seconds: int) -> bool:
        return bool(await self._client.set(LEADER_LOCK_KEY, self._owner_id, nx=True, ex=ttl_seconds))

    async def renew(self, ttl_seconds: int) -> bool:
        current = await self._client.get(LEADER_LOCK_KEY)
        if current is None:
            return False
        owner = current.decode() if isinstance(current, bytes) else current
        if owner != self._owner_id:
            return False
        await self._client.expire(LEADER_LOCK_KEY, ttl_seconds)
        return True

    async def release(self) -> None:
        current = await self._client.get(LEADER_LOCK_KEY)
        if current:
            owner = current.decode() if isinstance(current, bytes) else current
            if owner == self._owner_id:
                await self._client.delete(LEADER_LOCK_KEY)


def create_redis_client(settings: Settings) -> redis.Redis[bytes]:
    return redis.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_timeout=None,
        socket_connect_timeout=5,
    )
