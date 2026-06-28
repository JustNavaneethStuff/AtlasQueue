from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

TASKS_SUBMITTED = Counter(
    "atlasqueue_tasks_submitted_total",
    "Total tasks submitted",
    ["task_name", "executor_type"],
)
TASKS_COMPLETED = Counter(
    "atlasqueue_tasks_completed_total",
    "Total tasks completed",
    ["task_name", "status"],
)
TASK_DURATION = Histogram(
    "atlasqueue_task_duration_seconds",
    "Task execution duration",
    ["task_name"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)
QUEUE_DEPTH = Gauge(
    "atlasqueue_queue_depth",
    "Current queue depth",
    ["queue"],
)
WORKERS_ACTIVE = Gauge(
    "atlasqueue_workers_active",
    "Number of active workers",
)
TASKS_CANCELLED = Counter(
    "atlasqueue_tasks_cancelled_total",
    "Total tasks cancelled",
)
TASKS_RETRIED = Counter(
    "atlasqueue_tasks_retried_total",
    "Total tasks manually retried from DLQ",
)
DLQ_DEPTH = Gauge(
    "atlasqueue_dlq_depth",
    "Current dead-letter queue depth",
)
HTTP_REQUESTS = Counter(
    "atlasqueue_http_requests_total",
    "HTTP requests processed",
    ["method", "endpoint", "status_code"],
)
HTTP_LATENCY = Histogram(
    "atlasqueue_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
SCHEDULER_TICKS = Counter(
    "atlasqueue_scheduler_ticks_total",
    "Scheduler loop iterations",
)
SCHEDULER_RELEASED = Counter(
    "atlasqueue_scheduler_tasks_released_total",
    "Scheduled tasks released to ready queue",
)


def metrics_response() -> bytes:
    return generate_latest()


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path.endswith("/metrics"):
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        endpoint = getattr(route, "path", request.url.path)
        HTTP_REQUESTS.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()
        HTTP_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
        return response
