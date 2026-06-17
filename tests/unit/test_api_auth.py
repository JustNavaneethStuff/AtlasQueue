import pytest
from httpx import ASGITransport, AsyncClient

from atlasqueue.api.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_submit_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/v1/tasks", json={"name": "echo", "payload": {}})
    assert response.status_code == 401
