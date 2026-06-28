from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import bcrypt
import jwt
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from atlasqueue.domain.exceptions import AuthenticationError, AuthorizationError
from atlasqueue.infrastructure.persistence.models import UserModel
from atlasqueue.shared.config import Settings, get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"
    WORKER = "worker"


class AuthContext:
    def __init__(self, *, subject: str, role: str, auth_type: str) -> None:
        self.subject = subject
        self.role = role
        self.auth_type = auth_type


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(*, subject: str, role: str, settings: Settings) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> AuthContext:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc
    subject = payload.get("sub")
    role = payload.get("role")
    if not subject or not role:
        raise AuthenticationError("Invalid token payload")
    return AuthContext(subject=str(subject), role=str(role), auth_type="jwt")


async def authenticate_user(session: AsyncSession, username: str, password: str) -> AuthContext | None:
    from sqlalchemy import select

    result = await session.execute(select(UserModel).where(UserModel.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return AuthContext(subject=user.username, role=user.role, auth_type="jwt")


async def ensure_default_admin(session: AsyncSession, settings: Settings) -> None:
    from sqlalchemy import select

    result = await session.execute(select(UserModel).where(UserModel.username == settings.admin_username))
    if result.scalar_one_or_none():
        return
    session.add(
        UserModel(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role=UserRole.ADMIN.value,
        )
    )
    await session.flush()


async def resolve_auth(
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    if bearer and bearer.credentials:
        return decode_access_token(bearer.credentials, settings)
    if api_key and secrets.compare_digest(api_key, settings.api_key):
        return AuthContext(subject="api-key", role=UserRole.ADMIN.value, auth_type="api_key")
    raise AuthenticationError("Invalid or missing credentials")


async def verify_api_key_or_jwt(auth: AuthContext = Depends(resolve_auth)) -> str:
    return auth.subject


def require_role(*roles: str) -> Callable[..., Awaitable[str]]:
    async def _require(auth: AuthContext = Depends(resolve_auth)) -> str:
        if auth.role not in roles:
            raise AuthorizationError(f"Role '{auth.role}' is not authorized for this operation")
        return auth.subject

    return _require


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    if not api_key or not secrets.compare_digest(api_key, settings.api_key):
        raise AuthenticationError("Invalid or missing API key")
    return api_key
