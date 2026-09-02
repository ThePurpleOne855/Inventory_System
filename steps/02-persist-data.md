# Phase 2 — Give the app somewhere to persist data

**Why now, before routers:** routers and services both depend on a working `Session`. Build the
session dependency once, correctly, instead of stubbing endpoints now and wiring the session in
later.

## Checklist

- [x] Add `hashed_password: str` to the `Client` model (`app/models/client.py`) — present as a
      plain required `str` field (line 15). Note: nothing currently writes to it correctly yet —
      see Phase 3, `register_client_service` still builds the wrong object type.
- [x] Build `app/database.py` — real `engine` (`create_engine(DATABASE_URL, echo=True)`) and a
      `get_session()` generator, plus a `create_db_and_tables()` helper. Reads `DATABASE_URL` from
      `.env` via `python-dotenv`. Not yet wired into any router via `Depends` (that's Phase 4).
- [x] Add missing dependencies to `pyproject.toml`: `argon2-cffi>=25.1.0` and
      `psycopg2-binary>=2.9.12` are both present (root `pyproject.toml`, not the app subdirectory).
- [x] `alembic init` + first migration — **done and verified.** `.env` was also fixed to match
      `docker-compose.yaml`'s actual credentials (`madre_tierra_user`/`madre_tierra_db`, was
      pointing at a nonexistent `postgres`/`root` login before). `Madre_Tierra_Inventory_System/
      alembic/env.py` loads `.env`, overrides `sqlalchemy.url` from `DATABASE_URL`, and imports
      `Client`/`Order`/`Product` to populate `SQLModel.metadata`. The generated migration
      (`6952ae074881_initial_schema.py`) creates `client`, `product`, `orders` (FK-safe order,
      correct indexes) and was applied with `alembic upgrade head` — `alembic current` confirms
      the DB is stamped at `6952ae074881 (head)`.

  **Caveat, not blocking:** `env.py` has no `sys.path.insert(...)` for the `app` package.
  Confirmed it only resolves `from app.models import ...` when Alembic is run with cwd =
  `Madre_Tierra_Inventory_System/` (`cd Madre_Tierra_Inventory_System && uv run alembic ...`).
  Running the same command from the repo root fails with `ModuleNotFoundError: No module named
  'app'`. Fine for now as long as that convention is followed; worth hardening later with an
  explicit `sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))` in `env.py` so it
  works regardless of invocation directory.

## Done when

`get_session()` yields a working `Session` against the docker-compose Postgres ✅, and the first
Alembic migration applies cleanly ✅ — **Phase 2 is complete.**
