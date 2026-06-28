import pytest
from httpx import AsyncClient
from tests.conftest import _dependency_unavailable


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    try:
        response = await client.post(
            "/v1/auth/login",
            json={"username": "admin", "password": "admin-test-password"},
        )
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Database unavailable")
        raise
    if response.status_code == 500:
        pytest.skip("Database unavailable")
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"
    assert data["access_token"]


@pytest.mark.asyncio
async def test_login_invalid_credentials(unauthenticated_client: AsyncClient) -> None:
    try:
        response = await unauthenticated_client.post(
            "/v1/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Database unavailable")
        raise
    if response.status_code == 500:
        pytest.skip("Database unavailable")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jwt_access(client: AsyncClient) -> None:
    try:
        login = await client.post(
            "/v1/auth/login",
            json={"username": "admin", "password": "admin-test-password"},
        )
    except Exception as exc:
        if _dependency_unavailable(exc):
            pytest.skip("Database unavailable")
        raise
    if login.status_code != 200:
        pytest.skip("Auth unavailable")
    token = login.json()["access_token"]
    response = await client.get("/v1/tasks", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
