from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://atlas:atlas@localhost:5432/atlasqueue",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_key: str = Field(default="dev-api-key", alias="API_KEY")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    worker_id: str = Field(default="", alias="WORKER_ID")
    worker_tasks_module: str = Field(
        default="atlasqueue.worker.example_tasks",
        alias="WORKER_TASKS_MODULE",
    )
    worker_concurrency: int = Field(default=4, alias="WORKER_CONCURRENCY")
    worker_api_key: str = Field(default="dev-api-key", alias="WORKER_API_KEY")
    worker_heartbeat_interval: int = Field(default=10, alias="WORKER_HEARTBEAT_INTERVAL")

    scheduler_tick_interval: float = Field(default=1.0, alias="SCHEDULER_TICK_INTERVAL")
    scheduler_lock_ttl: int = Field(default=30, alias="SCHEDULER_LOCK_TTL")
    scheduler_batch_size: int = Field(default=100, alias="SCHEDULER_BATCH_SIZE")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")
    otel_exporter_otlp_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_service_name: str = Field(default="atlasqueue", alias="OTEL_SERVICE_NAME")

    block_private_webhook_urls: bool = Field(default=True, alias="BLOCK_PRIVATE_WEBHOOK_URLS")

    max_payload_bytes: int = Field(default=1_048_576, alias="MAX_PAYLOAD_BYTES")
    priority_levels: int = Field(default=4, alias="PRIORITY_LEVELS")
    default_max_retries: int = Field(default=3, alias="DEFAULT_MAX_RETRIES")
    default_retry_delay_seconds: int = Field(default=5, alias="DEFAULT_RETRY_DELAY_SECONDS")
    default_task_timeout_seconds: int = Field(default=300, alias="DEFAULT_TASK_TIMEOUT_SECONDS")

    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin-change-me", alias="ADMIN_PASSWORD")

    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")
    rate_limit_per_minute: int = Field(default=120, alias="RATE_LIMIT_PER_MINUTE")
    metrics_require_auth: bool = Field(default=False, alias="METRICS_REQUIRE_AUTH")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
