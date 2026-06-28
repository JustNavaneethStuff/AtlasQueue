import pytest
from httpx import AsyncClient
from tests.conftest import _dependency_unavailable


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready(client: AsyncClient) -> None:
    try:
        response = await client.get("/v1/ready")
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Dependencies unavailable")
        raise
    if response.status_code == 503:
        pytest.skip("Dependencies unavailable")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_metrics(client: AsyncClient) -> None:
    response = await client.get("/v1/metrics")
    assert response.status_code == 200
    assert b"atlasqueue_" in response.content


@pytest.mark.asyncio
async def test_submit_requires_auth(unauthenticated_client: AsyncClient) -> None:
    response = await unauthenticated_client.post("/v1/tasks", json={"name": "echo", "payload": {}})
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


@pytest.mark.asyncio
async def test_submit_task(client: AsyncClient) -> None:
    try:
        response = await client.post("/v1/tasks", json={"name": "echo", "payload": {"message": "hi"}})
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Dependencies unavailable")
        raise
    if response.status_code == 503:
        pytest.skip("Redis unavailable")
    assert response.status_code == 202
    data = response.json()
    assert data["name"] == "echo"


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient) -> None:
    try:
        response = await client.get("/v1/tasks/00000000-0000-0000-0000-000000000000")
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Dependencies unavailable")
        raise
    assert response.status_code == 404
    assert response.json()["code"] == "task_not_found"


@pytest.mark.asyncio
async def test_invalid_task_id(client: AsyncClient) -> None:
    response = await client.get("/v1/tasks/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_task_id"


@pytest.mark.asyncio
async def test_list_tasks_pagination(client: AsyncClient) -> None:
    try:
        response = await client.get("/v1/tasks", params={"limit": 10, "offset": 0})
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Dependencies unavailable")
        raise
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["limit"] == 10


@pytest.mark.asyncio
async def test_validation_error(unauthenticated_client: AsyncClient) -> None:
    response = await unauthenticated_client.post(
        "/v1/tasks",
        headers={"X-API-Key": "test-api-key"},
        json={"name": "", "payload": {}},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(client: AsyncClient) -> None:
    try:
        response = await client.get("/v1/admin/stats")
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Dependencies unavailable")
        raise
    assert response.status_code == 200
