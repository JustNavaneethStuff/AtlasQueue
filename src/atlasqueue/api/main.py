from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from atlasqueue.api.errors import register_exception_handlers
from atlasqueue.api.middleware.auth import verify_api_key_or_jwt
from atlasqueue.api.middleware.request_id import RequestIdMiddleware
from atlasqueue.api.rate_limit import limiter
from atlasqueue.api.routes.auth import router as auth_router
from atlasqueue.api.routes.v1 import router as v1_router
from atlasqueue.infrastructure.di.container import get_container
from atlasqueue.infrastructure.observability.metrics import PrometheusMiddleware
from atlasqueue.infrastructure.observability.telemetry import instrument_fastapi, setup_telemetry
from atlasqueue.shared.config import get_settings
from atlasqueue.shared.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    setup_logging(settings)
    setup_telemetry(settings, "atlasqueue-api")
    container = get_container()
    async with container.session() as session:
        from atlasqueue.api.middleware.auth import ensure_default_admin

        await ensure_default_admin(session, settings)
    yield
    await container.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Atlas Queue",
        description="Production-quality distributed task queue",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    register_exception_handlers(app)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(PrometheusMiddleware)
    app.include_router(auth_router, prefix="/v1")
    app.include_router(v1_router, prefix="/v1")
    instrument_fastapi(app)

    def custom_openapi() -> dict[str, object]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})
        schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
        schema["components"]["securitySchemes"]["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    if settings.metrics_require_auth:
        from fastapi import Response

        from atlasqueue.infrastructure.observability.metrics import metrics_response

        @app.get("/v1/metrics", include_in_schema=False)
        async def protected_metrics(_: str = Depends(verify_api_key_or_jwt)) -> Response:
            return Response(content=metrics_response(), media_type="text/plain; version=0.0.4")

    return app


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "atlasqueue.api.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
