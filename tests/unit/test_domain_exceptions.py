from atlasqueue.domain.exceptions import InvalidTaskStateError, TaskNotFoundError


def test_task_not_found_error() -> None:
    exc = TaskNotFoundError("abc")
    assert exc.code == "task_not_found"
    assert "abc" in exc.message


def test_invalid_task_state_error() -> None:
    exc = InvalidTaskStateError("bad state")
    assert exc.code == "invalid_task_state"
