"""Authentication for one configured inventory operator."""
import hashlib
import os
import secrets
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Annotated

from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.database import get_session
from app.models.auth_session import AuthSession

AUTH_FILE = Path(__file__).resolve().parents[3] / ".env.auth"
load_dotenv(AUTH_FILE)
SESSION_SECONDS = 8 * 60 * 60
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class OperatorSettings:
    username: str
    password_hash: str

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            (self.username + "\0" + self.password_hash).encode()
        ).hexdigest()


def get_operator_settings() -> OperatorSettings:
    username = os.getenv("AUTH_USERNAME", "").strip()
    password_hash = os.getenv("AUTH_PASSWORD_HASH", "")
    try:
        extract_parameters(password_hash)
    except (InvalidHashError, ValueError):
        raise HTTPException(503, "Operator authentication is not configured") from None
    if not username:
        raise HTTPException(503, "Operator authentication is not configured")
    return OperatorSettings(username, password_hash)


def utc_now() -> datetime:
    # Store UTC without an offset to match the database's timestamp column.
    return datetime.now(UTC).replace(tzinfo=None)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_operator(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[OperatorSettings, Depends(get_operator_settings)],
) -> AuthSession:
    if credentials is None or len(credentials.credentials) > 256:
        raise unauthorized()
    login = session.get(AuthSession, token_digest(credentials.credentials))
    if (
        login is None
        or login.expires_at <= utc_now()
        or not secrets.compare_digest(login.credentials_fingerprint, settings.fingerprint)
    ):
        raise unauthorized()
    return login


class LoginLimiter:
    """Bound password checks to five per minute per application process."""

    def __init__(self):
        self.attempts: deque[float] = deque()
        self.lock = Lock()

    def check(self) -> None:
        with self.lock:
            now = time.monotonic()
            while self.attempts and self.attempts[0] <= now - 60:
                self.attempts.popleft()
            if len(self.attempts) >= 5:
                retry_after = max(1, int(60 - (now - self.attempts[0])) + 1)
                raise HTTPException(
                    429, "Too many login attempts; try again shortly",
                    headers={"Retry-After": str(retry_after)},
                )
            self.attempts.append(now)


login_limiter = LoginLimiter()
