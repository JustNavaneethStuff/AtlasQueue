import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from atlasqueue.api.main import create_app
from atlasqueue.infrastructure.persistence.models import Base


@pytest.fixture(scope="module")
def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://atlas:atlas@localhost:5432/atlasqueue",
    )


@pytest_asyncio.fixture
async def engine(database_url: str):
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
def app():
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": os.environ.get("API_KEY", "test-api-key")}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac


@pytest.mark.asyncio
@pytest.mark.integration
async def test_submit_and_get_task(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/tasks",
        json={"name": "echo", "payload": {"message": "test"}, "priority": 0},
    )
    if response.status_code == 503:
        pytest.skip("Redis unavailable")
    assert response.status_code == 202
    data = response.json()
    task_id = data["id"]
    assert data["status"] in ("queued", "scheduled")

    get_response = await client.get(f"/v1/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "echo"
