from datetime import timedelta

import pytest
from sqlmodel import Session, select

from app.core.security import verify_password


def login(api, username="admin", password="operator-test-password"):
    return api.post("/auth/login", json={"username": username, "password": password})


@pytest.mark.parametrize("method,path", [
    ("get", "/clients/"), ("post", "/clients/"), ("get", "/clients/search"),
    ("get", "/clients/by-email?email=test@example.com"), ("get", "/clients/1"),
    ("put", "/clients/1"), ("delete", "/clients/1"),
    ("get", "/products/"), ("post", "/products/"), ("get", "/products/1"),
    ("put", "/products/1"), ("delete", "/products/1"),
    ("get", "/orders/"), ("post", "/orders/"), ("get", "/orders/1"),
    ("put", "/orders/1"), ("delete", "/orders/1"),
    ("get", "/orders/1/items"), ("post", "/orders/1/items"),
    ("delete", "/orders/1/items/1"), ("get", "/auth/me"), ("post", "/auth/logout"),
])
def test_all_data_routes_require_authentication(raw_api, method, path):
    response = raw_api.request(method, path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_me_logout_and_hashed_storage(raw_api, db_engine):
    from app.core.auth import token_digest
    from app.models.auth_session import AuthSession

    response = login(raw_api)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 28800
    with Session(db_engine) as session:
        stored = session.exec(select(AuthSession)).one()
        assert stored.token_hash == token_digest(token)
        assert token not in stored.model_dump().values()
    raw_api.headers["Authorization"] = f"Bearer {token}"
    assert raw_api.get("/auth/me").json() == {"username": "admin"}
    assert raw_api.get("/products/").status_code == 200
    response = raw_api.post("/auth/logout")
    assert response.status_code == 204
    assert response.content == b""
    assert raw_api.get("/products/").status_code == 401
    assert raw_api.post("/auth/logout").status_code == 401


@pytest.mark.parametrize("username,password", [
    ("admin", "wrong-password"), ("someone", "operator-test-password"),
])
def test_bad_credentials(raw_api, username, password, db_engine):
    from app.models.auth_session import AuthSession

    response = login(raw_api, username, password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired credentials"
    with Session(db_engine) as session:
        assert session.exec(select(AuthSession)).all() == []


@pytest.mark.parametrize("header", ["Bearer invalid", "Basic abc", "Bearer", "Bearer " + "a" * 257])
def test_invalid_tokens(raw_api, header):
    assert raw_api.get("/auth/me", headers={"Authorization": header}).status_code == 401


def test_expired_session_and_cleanup(raw_api, db_engine):
    from app.core.auth import utc_now
    from app.models.auth_session import AuthSession

    token = login(raw_api).json()["access_token"]
    with Session(db_engine) as session:
        stored = session.exec(select(AuthSession)).one()
        stored.expires_at = utc_now() - timedelta(seconds=1)
        session.add(stored)
        session.commit()
    assert raw_api.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert login(raw_api).status_code == 200
    with Session(db_engine) as session:
        assert len(session.exec(select(AuthSession)).all()) == 1


def test_password_rotation_revokes_existing_sessions(api, monkeypatch):
    from app.core.security import hash_password

    monkeypatch.setenv("AUTH_PASSWORD_HASH", hash_password("replacement-password"))
    assert api.get("/auth/me").status_code == 401
    assert login(api).status_code == 401
    assert login(api, password="replacement-password").status_code == 200


@pytest.mark.parametrize("key,value", [("AUTH_USERNAME", ""), ("AUTH_PASSWORD_HASH", ""), ("AUTH_PASSWORD_HASH", "invalid")])
def test_missing_or_invalid_configuration_fails_closed(raw_api, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    assert login(raw_api).status_code == 503
    assert raw_api.get("/products/").status_code == 503


def test_login_throttle_recovers_after_window(raw_api, monkeypatch):
    from app.core import auth

    clock = [100.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: clock[0])
    for _ in range(5):
        assert login(raw_api, password="wrong").status_code == 401
    response = login(raw_api)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
    clock[0] += 61
    assert login(raw_api).status_code == 200


def test_openapi_security_and_no_public_registration(raw_api):
    paths = raw_api.get("/openapi.json").json()["paths"]
    for path, operations in paths.items():
        for operation in operations.values():
            if path != "/auth/login":
                assert operation["security"] == [{"HTTPBearer": []}]
    assert "/auth/register" not in paths
    assert not paths["/auth/login"]["post"].get("security")


def test_invalid_password_hash_returns_false():
    assert verify_password("password", "invalid") is False


def test_setup_stores_only_hash_and_requires_explicit_rotation(tmp_path, monkeypatch):
    from app.core import setup_auth
    from dotenv import dotenv_values

    target = tmp_path / ".env.auth"
    monkeypatch.setattr(setup_auth, "AUTH_FILE", target)
    monkeypatch.setattr("sys.argv", ["setup_auth"])
    monkeypatch.setattr("builtins.input", lambda _: "admin")
    monkeypatch.setattr(setup_auth.getpass, "getpass", lambda _: "operator-test-password")
    setup_auth.main()
    values = dotenv_values(target)
    assert values["AUTH_USERNAME"] == "admin"
    assert verify_password("operator-test-password", values["AUTH_PASSWORD_HASH"])
    assert "operator-test-password" not in target.read_text()
    assert target.stat().st_mode & 0o777 == 0o600
    with pytest.raises(SystemExit):
        setup_auth.main()


def test_auth_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    project = Path(__file__).resolve().parents[2]
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(project / "alembic.ini"))
    config.set_main_option("script_location", str(project / "alembic"))
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert {column["name"] for column in inspect(engine).get_columns("auth_session")} == {
            "token_hash", "credentials_fingerprint", "expires_at",
        }
        command.downgrade(config, "6952ae074881")
        assert "auth_session" not in inspect(engine).get_table_names()
        assert "client" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
