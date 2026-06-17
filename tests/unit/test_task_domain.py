import pytest

from atlasqueue.domain.entities.task import BackoffPolicy, Priority, Task
from atlasqueue.domain.value_objects.enums import ExecutorType, TaskStatus


def test_task_create_immediate() -> None:
    task = Task.create(
        name="echo",
        executor_type=ExecutorType.PYTHON,
        payload={"message": "hi"},
        priority=Priority.normal(),
        max_retries=3,
    )
    assert task.status == TaskStatus.PENDING
    assert task.name == "echo"


def test_task_transition_valid() -> None:
    task = Task.create(
        name="echo",
        executor_type=ExecutorType.PYTHON,
        payload={},
        priority=Priority(0),
        max_retries=1,
    )
    task.transition_to(TaskStatus.QUEUED)
    assert task.status == TaskStatus.QUEUED


def test_task_transition_invalid() -> None:
    task = Task.create(
        name="echo",
        executor_type=ExecutorType.PYTHON,
        payload={},
        priority=Priority(0),
        max_retries=1,
    )
    with pytest.raises(ValueError, match="Invalid transition"):
        task.transition_to(TaskStatus.COMPLETED)


def test_backoff_exponential() -> None:
    policy = BackoffPolicy(strategy="exponential", base_delay_seconds=5, multiplier=2.0)
    assert policy.delay_for_attempt(1) == 5
    assert policy.delay_for_attempt(2) == 10
    assert policy.delay_for_attempt(3) == 20


def test_backoff_fixed() -> None:
    policy = BackoffPolicy(strategy="fixed", base_delay_seconds=7)
    assert policy.delay_for_attempt(5) == 7


def test_can_retry() -> None:
    task = Task.create(
        name="fail",
        executor_type=ExecutorType.PYTHON,
        payload={},
        priority=Priority(0),
        max_retries=3,
    )
    task.attempts = 2
    assert task.can_retry()
    task.attempts = 3
    assert not task.can_retry()
