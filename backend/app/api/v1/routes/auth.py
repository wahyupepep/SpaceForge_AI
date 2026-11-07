from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.api.dependencies import get_auth_service
from app.core.config import settings
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.auth import SESSION_COOKIE, AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


def _set_session_cookie(response: Response, token: str, expires_at) -> None:  # type: ignore[no-untyped-def]
    response.set_cookie(
        SESSION_COOKIE,
        token,
        expires=expires_at,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        path="/",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, response: Response, service: AuthServiceDependency
) -> AuthResponse:
    user, token, expires_at = await service.register(payload)
    _set_session_cookie(response, token, expires_at)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest, response: Response, service: AuthServiceDependency
) -> AuthResponse:
    user, token, expires_at = await service.login(payload)
    _set_session_cookie(response, token, expires_at)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.get("/me", response_model=AuthResponse)
async def me(
    service: AuthServiceDependency,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> AuthResponse:
    user = await service.current_user(token)
    if user is None:
        raise AuthError("Sign in to continue.")
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    service: AuthServiceDependency,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    await service.logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/")
