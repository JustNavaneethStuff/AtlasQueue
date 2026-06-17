from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from atlasqueue.api.middleware.auth import verify_api_key
from atlasqueue.application.dto.mappers import task_to_response
from atlasqueue.application.dto.task_dto import (
    AdminStatsResponse,
    ErrorResponse,
    HealthResponse,
    RegisterWorkerRequest,
    SubmitTaskRequest,
    TaskEventResponse,
    TaskListResponse,
    TaskResponse,
    WorkerResponse,
)
from atlasqueue.domain.entities.task import TaskId
from atlasqueue.domain.value_objects.enums import TaskStatus
from atlasqueue.infrastructure.di.container import Container, get_container
from atlasqueue.infrastructure.observability.metrics import (
    QUEUE_DEPTH,
    WORKERS_ACTIVE,
    metrics_response,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def ready(container: Container = Depends(get_container)) -> HealthResponse:
    try:
        await container.redis.ping()
        async with container.session() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Not ready: {exc}") from exc
    return HealthResponse(status="ready")


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=metrics_response(), media_type="text/plain; version=0.0.4")


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def submit_task(
    request: SubmitTaskRequest,
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> TaskResponse:
    try:
        async with container.session() as session:
            manager = await container.queue_manager(session)
            task = await manager.submit(request)
            return task_to_response(task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Enqueue failed: {exc}") from exc


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> TaskResponse:
    async with container.session() as session:
        manager = await container.queue_manager(session)
        task = await manager.get_task(TaskId.from_string(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_to_response(task)


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> TaskListResponse:
    async with container.session() as session:
        manager = await container.queue_manager(session)
        tasks = await manager.list_tasks(status=status_filter, limit=limit, offset=offset)
        return TaskListResponse(
            tasks=[task_to_response(t) for t in tasks],
            total=len(tasks),
        )


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> TaskResponse:
    try:
        async with container.session() as session:
            service = await container.cancellation_service(session)
            task = await service.cancel(TaskId.from_string(task_id))
            return task_to_response(task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> TaskResponse:
    try:
        async with container.session() as session:
            manager = await container.queue_manager(session)
            task = await manager.retry_task(TaskId.from_string(task_id))
            return task_to_response(task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/events", response_model=list[TaskEventResponse])
async def get_task_events(
    task_id: str,
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> list[TaskEventResponse]:
    from atlasqueue.infrastructure.persistence.repositories import SqlAlchemyTaskEventRepository

    async with container.session() as session:
        repo = SqlAlchemyTaskEventRepository(session)
        events = await repo.list_for_task(TaskId.from_string(task_id))
        return [
            TaskEventResponse(
                id=str(e.id),
                event_type=e.event_type,
                from_status=e.from_status.value if e.from_status else None,
                to_status=e.to_status.value if e.to_status else None,
                message=e.message,
                metadata=e.metadata,
                created_at=e.created_at,
            )
            for e in events
        ]


@router.post("/workers/register", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
async def register_worker(
    request: RegisterWorkerRequest,
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> WorkerResponse:
    async with container.session() as session:
        registry = await container.worker_registry(session)
        worker = await registry.register(request.hostname, request.metadata)
        return WorkerResponse(
            id=str(worker.id),
            hostname=worker.hostname,
            status=worker.status.value,
            registered_at=worker.registered_at,
            last_seen_at=worker.last_seen_at,
            metadata=worker.metadata,
        )


@router.get("/workers", response_model=list[WorkerResponse])
async def list_workers(
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> list[WorkerResponse]:
    async with container.session() as session:
        registry = await container.worker_registry(session)
        workers = await registry.list_workers()
        return [
            WorkerResponse(
                id=str(w.id),
                hostname=w.hostname,
                status=w.status.value,
                registered_at=w.registered_at,
                last_seen_at=w.last_seen_at,
                metadata=w.metadata,
            )
            for w in workers
        ]


@router.get("/admin/stats", response_model=AdminStatsResponse)
async def admin_stats(
    _: str = Depends(verify_api_key),
    container: Container = Depends(get_container),
) -> AdminStatsResponse:
    async with container.session() as session:
        registry = await container.worker_registry(session)
        from atlasqueue.infrastructure.persistence.repositories import SqlAlchemyTaskRepository

        task_repo = SqlAlchemyTaskRepository(session)
        tasks_by_status = await task_repo.count_by_status()
        depths = await container.queue_backend().queue_depths()
        for queue_name, depth in depths.items():
            QUEUE_DEPTH.labels(queue=queue_name).set(depth)
        workers = await registry.list_workers()
        active_redis = await container.queue_backend().get_active_workers()
        WORKERS_ACTIVE.set(len(active_redis))
        return AdminStatsResponse(
            tasks_by_status=tasks_by_status,
            queue_depths=depths,
            active_workers=len(active_redis),
            workers=[
                WorkerResponse(
                    id=str(w.id),
                    hostname=w.hostname,
                    status=w.status.value,
                    registered_at=w.registered_at,
                    last_seen_at=w.last_seen_at,
                    metadata=w.metadata,
                )
                for w in workers
            ],
        )
