from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from atlasqueue.application.dto.task_dto import ErrorResponse
from atlasqueue.domain.exceptions import (
    AtlasQueueError,
    AuthenticationError,
    AuthorizationError,
    EnqueueFailedError,
    InvalidTaskIdError,
    InvalidTaskStateError,
    PayloadTooLargeError,
    TaskNotFoundError,
)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(
    *,
    status_code: int,
    detail: str,
    code: str,
    request: Request,
) -> JSONResponse:
    body = ErrorResponse(detail=detail, code=code, request_id=_request_id(request))
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(TaskNotFoundError)
    async def task_not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(InvalidTaskIdError)
    async def invalid_task_id_handler(request: Request, exc: InvalidTaskIdError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(InvalidTaskStateError)
    async def invalid_task_state_handler(request: Request, exc: InvalidTaskStateError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(PayloadTooLargeError)
    async def payload_too_large_handler(request: Request, exc: PayloadTooLargeError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(EnqueueFailedError)
    async def enqueue_failed_handler(request: Request, exc: EnqueueFailedError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(AtlasQueueError)
    async def atlasqueue_error_handler(request: Request, exc: AtlasQueueError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
            code=exc.code,
            request=request,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        body = ErrorResponse(
            detail="Request validation failed",
            code="validation_error",
            request_id=_request_id(request),
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(exclude_none=True),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        body = ErrorResponse(
            detail="Validation failed",
            code="validation_error",
            request_id=_request_id(request),
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(exclude_none=True),
        )
