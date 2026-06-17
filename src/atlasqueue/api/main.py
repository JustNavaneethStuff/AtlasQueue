from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlasqueue.api.middleware.request_id import RequestIdMiddleware
from atlasqueue.api.routes.v1 import router as v1_router
from atlasqueue.infrastructure.di.container import get_container
from atlasqueue.infrastructure.observability.telemetry import instrument_fastapi, setup_telemetry
from atlasqueue.shared.config import get_settings
from atlasqueue.shared.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    setup_logging(settings)
    setup_telemetry(settings, "atlasqueue-api")
    yield
    await get_container().close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Atlas Queue",
        description="Production-quality distributed task queue",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(v1_router, prefix="/v1")
    instrument_fastapi(app)
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
