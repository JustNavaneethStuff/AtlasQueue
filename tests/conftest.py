import os

import pytest

# Set test env before settings are cached
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("WORKER_API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://atlas:atlas@localhost:5432/atlasqueue")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session", autouse=True)
def _clear_settings_cache() -> None:
    from atlasqueue.shared.config import get_settings

    get_settings.cache_clear()
