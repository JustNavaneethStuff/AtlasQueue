from __future__ import annotations

from typing import Any

import httpx

from atlasqueue.domain.entities.task import Task
from atlasqueue.shared.config import Settings
from atlasqueue.shared.logging import get_logger

logger = get_logger(__name__)


class WebhookValidationError(Exception):
    pass


def validate_webhook_url(url: str, settings: Settings) -> None:
    if not settings.block_private_webhook_urls:
        return
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        msg = f"Unsupported webhook scheme: {parsed.scheme}"
        raise WebhookValidationError(msg)
    host = (parsed.hostname or "").lower()
    blocked = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if host in blocked or host.startswith("10.") or host.startswith("192.168.") or host.startswith("172."):
        msg = f"Webhook URL targets private network: {host}"
        raise WebhookValidationError(msg)


class WebhookExecutor:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient()

    async def execute(self, task: Task) -> dict[str, Any]:
        payload = task.payload
        url = payload.get("url")
        if not url:
            msg = "Webhook payload must include 'url'"
            raise ValueError(msg)
        validate_webhook_url(str(url), self._settings)
        method = str(payload.get("method", "POST")).upper()
        headers = payload.get("headers") or {}
        body = payload.get("body", payload.get("data", {}))
        timeout = task.timeout_seconds
        response = await self._client.request(
            method,
            str(url),
            headers=headers,
            json=body if isinstance(body, dict) else None,
            content=None if isinstance(body, dict) else str(body).encode(),
            timeout=timeout,
        )
        response.raise_for_status()
        try:
            data: Any = response.json()
        except ValueError:
            data = {"text": response.text}
        return {"status_code": response.status_code, "body": data}

    async def aclose(self) -> None:
        await self._client.aclose()
