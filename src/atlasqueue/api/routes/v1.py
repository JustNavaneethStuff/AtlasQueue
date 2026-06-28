from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import Response

from atlasqueue.api.middleware.auth import require_role, verify_api_key_or_jwt
from atlasqueue.api.rate_limit import limiter
from atlasqueue.application.dto.mappers import task_event_to_response, task_to_response, worker_to_response
from atlasqueue.application.dto.task_dto import (
    AdminStatsResponse,
    HealthResponse,
    RegisterWorkerRequest,
    SubmitTaskRequest,
    TaskEventResponse,
    TaskListResponse,
    TaskResponse,
    WorkerResponse,
)
from atlasqueue.domain.entities.task import TaskId
from atlasqueue.domain.exceptions import InvalidTaskIdError
from atlasqueue.domain.value_objects.enums import TaskStatus
from atlasqueue.infrastructure.di.container import Container, get_container
from atlasqueue.infrastructure.observability.metrics import (
    QUEUE_DEPTH,
    WORKERS_ACTIVE,
    metrics_response,
)

router = APIRouter()


def _parse_task_id(task_id: str) -> TaskId:
    try:
        return TaskId.from_string(task_id)
    except ValueError as exc:
        raise InvalidTaskIdError(task_id) from exc


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Liveness probe",
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    tags=["health"],
    summary="Readiness probe",
)
async def ready(container: Container = Depends(get_container)) -> HealthResponse:
    await container.redis.ping()
    async with container.session() as session:
        await session.execute(__import__("sqlalchemy").text("SELECT 1"))
    return HealthResponse(status="ready")


@router.get("/metrics", tags=["observability"], summary="Prometheus metrics")
async def metrics() -> Response:
    return Response(content=metrics_response(), media_type="text/plain; version=0.0.4")


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["tasks"],
    summary="Submit a task",
)
@limiter.limit("60/minute")
async def submit_task(
    request: Request,
    body: SubmitTaskRequest,
    _: str = Depends(require_role("admin", "user")),
    container: Container = Depends(get_container),
) -> TaskResponse:
    async with container.session() as session:
        manager = await container.queue_manager(session)
        task = await manager.submit(body)
        return task_to_response(task)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    tags=["tasks"],
    summary="Get task by ID",
)
async def get_task(
    task_id: str,
    _: str = Depends(verify_api_key_or_jwt),
    container: Container = Depends(get_container),
) -> TaskResponse:
    parsed_id = _parse_task_id(task_id)
    async with container.session() as session:
        manager = await container.queue_manager(session)
        task = await manager.get_task_or_raise(parsed_id)
        return task_to_response(task)


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    tags=["tasks"],
    summary="List tasks",
)
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    name: str | None = Query(default=None, min_length=1, max_length=255),
    sort_by: str = Query(default="created_at", pattern="^(created_at|priority|status|name)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(verify_api_key_or_jwt),
    container: Container = Depends(get_container),
) -> TaskListResponse:
    async with container.session() as session:
        manager = await container.queue_manager(session)
        tasks = await manager.list_tasks(
            status=status_filter,
            name=name,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
        total = await manager.count_tasks(status=status_filter, name=name)
        return TaskListResponse(
            tasks=[task_to_response(t) for t in tasks],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskResponse,
    tags=["tasks"],
    summary="Cancel a task",
)
async def cancel_task(
    task_id: str,
    _: str = Depends(require_role("admin", "user")),
    container: Container = Depends(get_container),
) -> TaskResponse:
    parsed_id = _parse_task_id(task_id)
    async with container.session() as session:
        service = await container.cancellation_service(session)
        task = await service.cancel(parsed_id)
        return task_to_response(task)


@router.post(
    "/tasks/{task_id}/retry",
    response_model=TaskResponse,
    tags=["tasks"],
    summary="Retry a dead-letter task",
)
async def retry_task(
    task_id: str,
    _: str = Depends(require_role("admin")),
    container: Container = Depends(get_container),
) -> TaskResponse:
    parsed_id = _parse_task_id(task_id)
    async with container.session() as session:
        manager = await container.queue_manager(session)
        task = await manager.retry_task(parsed_id)
        return task_to_response(task)


@router.get(
    "/tasks/{task_id}/events",
    response_model=list[TaskEventResponse],
    tags=["tasks"],
    summary="List task audit events",
)
async def get_task_events(
    task_id: str,
    _: str = Depends(verify_api_key_or_jwt),
    container: Container = Depends(get_container),
) -> list[TaskEventResponse]:
    parsed_id = _parse_task_id(task_id)
    async with container.session() as session:
        manager = await container.queue_manager(session)
        events = await manager.get_task_events(parsed_id)
        return [task_event_to_response(e) for e in events]


@router.post(
    "/workers/register",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workers"],
    summary="Register a worker",
)
async def register_worker(
    request: RegisterWorkerRequest,
    _: str = Depends(require_role("admin", "worker")),
    container: Container = Depends(get_container),
) -> WorkerResponse:
    async with container.session() as session:
        registry = await container.worker_registry(session)
        worker = await registry.register(request.hostname, request.metadata)
        return worker_to_response(worker)


@router.get(
    "/workers",
    response_model=list[WorkerResponse],
    tags=["workers"],
    summary="List registered workers",
)
async def list_workers(
    _: str = Depends(verify_api_key_or_jwt),
    container: Container = Depends(get_container),
) -> list[WorkerResponse]:
    async with container.session() as session:
        registry = await container.worker_registry(session)
        workers = await registry.list_workers()
        return [worker_to_response(w) for w in workers]


@router.get(
    "/admin/stats",
    response_model=AdminStatsResponse,
    tags=["admin"],
    summary="Queue and worker statistics",
)
async def admin_stats(
    _: str = Depends(require_role("admin")),
    container: Container = Depends(get_container),
) -> AdminStatsResponse:
    async with container.session() as session:
        manager = await container.queue_manager(session)
        registry = await container.worker_registry(session)
        stats = await manager.get_admin_stats()
        depths = stats["queue_depths"]
        for queue_name, depth in depths.items():
            QUEUE_DEPTH.labels(queue=queue_name).set(depth)
        WORKERS_ACTIVE.set(stats["active_workers"])
        workers = await registry.list_workers()
        return AdminStatsResponse(
            tasks_by_status=stats["tasks_by_status"],
            queue_depths=depths,
            active_workers=stats["active_workers"],
            workers=[worker_to_response(w) for w in workers],
        )
