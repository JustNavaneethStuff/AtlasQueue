from __future__ import annotations

from fastapi import APIRouter, Depends

from atlasqueue.api.middleware.auth import authenticate_user, create_access_token, ensure_default_admin
from atlasqueue.application.dto.task_dto import LoginRequest, TokenResponse
from atlasqueue.domain.exceptions import AuthenticationError
from atlasqueue.infrastructure.di.container import Container, get_container
from atlasqueue.shared.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
)
async def login(
    request: LoginRequest,
    container: Container = Depends(get_container),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    async with container.session() as session:
        await ensure_default_admin(session, settings)
        auth = await authenticate_user(session, request.username, request.password)
        if not auth:
            raise AuthenticationError("Invalid username or password")
        token = create_access_token(subject=auth.subject, role=auth.role, settings=settings)
        return TokenResponse(access_token=token, role=auth.role)
