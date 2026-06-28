import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from atlasqueue.api.main import create_app
from atlasqueue.shared.config import get_settings


def _dependency_unavailable(exc: BaseException) -> bool:
    name = type(exc).__name__
    return name in {
        "ConnectionError",
        "ConnectionRefusedError",
        "InvalidPasswordError",
        "OperationalError",
        "TimeoutError",
    }


@pytest.fixture(scope="session", autouse=True)
def _configure_test_env() -> None:
    os.environ.setdefault("API_KEY", "test-api-key")
    os.environ.setdefault("WORKER_API_KEY", "test-api-key")
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://atlas:atlas@localhost:5432/atlasqueue")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
    os.environ.setdefault("ADMIN_USERNAME", "admin")
    os.environ.setdefault("ADMIN_PASSWORD", "admin-test-password")
    os.environ.setdefault("LOG_JSON", "false")
    get_settings.cache_clear()


@pytest.fixture
def app():
    get_settings.cache_clear()
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": os.environ["API_KEY"]}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac


@pytest_asyncio.fixture
async def unauthenticated_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
