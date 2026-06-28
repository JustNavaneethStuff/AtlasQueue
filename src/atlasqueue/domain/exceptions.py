from __future__ import annotations


class AtlasQueueError(Exception):
    """Base exception for domain and application errors."""

    def __init__(self, message: str, *, code: str = "internal_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class TaskNotFoundError(AtlasQueueError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task {task_id} not found", code="task_not_found")


class InvalidTaskStateError(AtlasQueueError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_task_state")


class EnqueueFailedError(AtlasQueueError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="enqueue_failed")


class PayloadTooLargeError(AtlasQueueError):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            f"Payload exceeds max size of {max_bytes} bytes",
            code="payload_too_large",
        )


class InvalidTaskIdError(AtlasQueueError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Invalid task id: {task_id}", code="invalid_task_id")


class AuthenticationError(AtlasQueueError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="authentication_failed")


class AuthorizationError(AtlasQueueError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, code="authorization_failed")
