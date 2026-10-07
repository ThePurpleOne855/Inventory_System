import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import hash_password


@pytest.fixture(scope="session")
def operator_hash():
    return hash_password("operator-test-password")


@pytest.fixture
def auth_environment(monkeypatch, operator_hash):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", operator_hash)


@pytest.fixture
def db_engine(auth_environment):
    import app.models  # Register every table before creating the test database.

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def raw_api(db_engine, monkeypatch):
    from app.core.auth import LoginLimiter
    from app.database import get_session
    from app.main import app

    monkeypatch.setattr("app.routers.auth.login_limiter", LoginLimiter())

    def session_override():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def api(raw_api):
    response = raw_api.post("/auth/login", json={
        "username": "admin", "password": "operator-test-password",
    })
    assert response.status_code == 200, response.text
    raw_api.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return raw_api
