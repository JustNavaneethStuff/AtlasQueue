from atlasqueue.worker.executor.python_executor import task

__all__ = ["task"]


@task(name="echo")
def echo(message: str = "hello") -> dict[str, str]:
    return {"message": message}


@task(name="add")
def add(a: int, b: int) -> dict[str, int]:
    return {"sum": a + b}


@task(name="fail_always")
def fail_always() -> None:
    raise RuntimeError("Intentional failure for DLQ testing")
