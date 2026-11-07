from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ApplicationError
from app.models.auth import User, UserSession
from app.models.project import Project
from app.schemas.auth import LoginRequest, RegisterRequest

SESSION_COOKIE = "spaceforge_session"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AuthError(ApplicationError):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__("AUTHENTICATION_FAILED", message, status_code)


def _password_hash(password: str, *, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), actual_salt, iterations, dklen=32
    )
    return f"pbkdf2_sha256${iterations}${actual_salt.hex()}${digest.hex()}"


def _password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, _expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256" or int(iterations_text) != 600_000:
            return False
        candidate = _password_hash(password, salt=bytes.fromhex(salt_hex))
        return hmac.compare_digest(candidate, encoded)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, payload: RegisterRequest) -> tuple[User, str, datetime]:
        email = payload.email.strip().lower()
        if not EMAIL_PATTERN.fullmatch(email):
            raise AuthError("Enter a valid email address.", 422)
        existing = await self._session.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise AuthError("An account with this email already exists.", 409)
        is_first_user = (await self._session.scalar(select(func.count(User.id))) or 0) == 0
        user = User(
            email=email,
            display_name=payload.display_name.strip(),
            password_hash=_password_hash(payload.password),
        )
        self._session.add(user)
        await self._session.flush()
        if is_first_user:
            await self._session.execute(
                update(Project).where(Project.owner_id.is_(None)).values(owner_id=user.id)
            )
        token, expires_at = self._new_session(user.id)
        await self._session.commit()
        await self._session.refresh(user)
        return user, token, expires_at

    async def login(self, payload: LoginRequest) -> tuple[User, str, datetime]:
        email = payload.email.strip().lower()
        user = await self._session.scalar(select(User).where(User.email == email))
        if user is None or not _password_matches(payload.password, user.password_hash):
            raise AuthError("Email or password is incorrect.")
        token, expires_at = self._new_session(user.id)
        await self._session.commit()
        return user, token, expires_at

    def _new_session(self, user_id: UUID) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        self._session.add(
            UserSession(user_id=user_id, token_hash=token_hash(token), expires_at=expires_at)
        )
        return token, expires_at

    async def current_user(self, token: str | None) -> User | None:
        if not token:
            return None
        result = await self._session.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(
                UserSession.token_hash == token_hash(token),
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        session = result.scalar_one_or_none()
        return session.user if session is not None else None

    async def logout(self, token: str | None) -> None:
        if token:
            await self._session.execute(
                delete(UserSession).where(UserSession.token_hash == token_hash(token))
            )
            await self._session.commit()
