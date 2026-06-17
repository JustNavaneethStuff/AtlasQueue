from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"
    ENQUEUE_FAILED = "enqueue_failed"


class ExecutorType(StrEnum):
    PYTHON = "python"
    WEBHOOK = "webhook"


class WorkerStatus(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"
