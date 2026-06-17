from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

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


def metrics_response() -> bytes:
    return generate_latest()
