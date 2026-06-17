from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

import httpx

from atlasqueue.application.dto.task_dto import BackoffPolicyDTO, SubmitTaskRequest


class AtlasQueueClient:
    def __init__(self, base_url: str, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(
            headers={"X-API-Key": api_key},
            timeout=30.0,
        )

    async def submit_task(
        self,
        name: str,
        *,
        payload: dict[str, Any] | None = None,
        executor_type: Literal["python", "webhook"] = "python",
        priority: int = 2,
        scheduled_at: datetime | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        backoff_policy: BackoffPolicyDTO | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        request = SubmitTaskRequest(
            name=name,
            executor_type=executor_type,
            payload=payload or {},
            priority=priority,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            backoff_policy=backoff_policy,
            idempotency_key=idempotency_key,
        )
        response = await self._client.post(
            f"{self._base_url}/v1/tasks",
            json=request.model_dump(mode="json"),
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def get_task(self, task_id: str) -> dict[str, Any]:
        response = await self._client.get(f"{self._base_url}/v1/tasks/{task_id}")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def cancel_task(self, task_id: str) -> dict[str, Any]:
        response = await self._client.post(f"{self._base_url}/v1/tasks/{task_id}/cancel")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def aclose(self) -> None:
        await self._client.aclose()
