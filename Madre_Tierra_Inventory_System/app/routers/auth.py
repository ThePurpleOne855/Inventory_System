import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlmodel import delete

from app.core.auth import (
    SESSION_SECONDS,
    OperatorSettings,
    get_operator_settings,
    login_limiter,
    require_operator,
    token_digest,
    unauthorized,
    utc_now,
)
from app.core.security import verify_password
from app.models.auth_session import AuthSession
from app.routers.dependencies import SessionDep
from app.schema.auth import LoginRequest, OperatorRead, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
SettingsDep = Annotated[OperatorSettings, Depends(get_operator_settings)]
OperatorSession = Annotated[AuthSession, Depends(require_operator)]


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response, session: SessionDep, settings: SettingsDep):
    login_limiter.check()
    password_matches = verify_password(data.password.get_secret_value(), settings.password_hash)
    username_matches = secrets.compare_digest(data.username.encode(), settings.username.encode())
    if not password_matches or not username_matches:
        raise unauthorized()

    token = secrets.token_urlsafe(32)
    now = utc_now()
    session.exec(delete(AuthSession).where(AuthSession.expires_at <= now))
    session.add(AuthSession(
        token_hash=token_digest(token),
        credentials_fingerprint=settings.fingerprint,
        expires_at=now + timedelta(seconds=SESSION_SECONDS),
    ))
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(access_token=token, expires_in=SESSION_SECONDS)


@router.get("/me", response_model=OperatorRead)
def current_operator(login: OperatorSession, settings: SettingsDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return OperatorRead(username=settings.username)


@router.post("/logout", status_code=204)
def logout(login: OperatorSession, session: SessionDep):
    session.delete(login)
    session.commit()
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
