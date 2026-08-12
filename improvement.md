# Improvement Plan — Madre Tierra Inventory System

_Last audited: 2026-08-09. This replaces the previous version of this file, which described an
earlier state of the repo (empty routers, missing `product.py`, a syntax error in `order.py`) —
that state no longer matches what's here. Treat this as the current source of truth; see
`Madre_Tierra_Inventory_System/app/models/EVALUATION.md` and
`Madre_Tierra_Inventory_System/app/routers/EVALUATION.md` for the file-by-file detail behind the
summary below._

## Where things stand right now

Real progress since the last audit: the project skeleton question is settled (only
`Madre_Tierra_Inventory_System/app/` remains — good), `product.py` now exists as both a model
and a schema, all three resources (`clients`, `orders`, `products`) have schema files and router
stubs with the right HTTP verbs, and the `order.py` model syntax error from the last audit is
fixed. The shape of the app is basically right. What's missing is what makes it actually run.

**Verified by actually importing/compiling the code, not just reading it:**

- `app/__init__.py` contains a stray `s` on its own line — importing the `app` package raises
  `NameError: name 's' is not defined`. This blocks importing anything under `app.*` right now:
  routers, models, everything. **This is the #1 fix** — until it's empty, nothing else in this
  plan can be tested end-to-end.
- `app/main.py` is empty. No `FastAPI()` instance, no `include_router(...)` calls anywhere. There
  is currently nothing for `uvicorn` to serve.
- `crud/client.py`, `crud/order.py`, `crud/product.py` are all still empty — no DB session
  dependency exists anywhere in the codebase either. Every router endpoint is a `pass` stub.
- `auth.py` and `analytics.py` (both under `app/routers/`) are empty files — not started.
- `models/order.py`'s `__tablename__="orders"` is written as a class keyword argument, which
  SQLModel silently ignores — the actual table name is still `order` (a reserved SQL word),
  confirmed by importing the model directly. Looked fixed on a skim; isn't.
- `OrderBase`/`Order` still use `user_id` for what should be `client_id` — there's no `User`
  model in this codebase, only `Client`.

Full detail on all of the above, plus router-specific bugs (a missing route decorator in
`products.py`, missing request-body parameters on several create/update endpoints, a stray
`FastAPI()` instance left inside `clients.py`), is in
[`app/routers/EVALUATION.md`](Madre_Tierra_Inventory_System/app/routers/EVALUATION.md) — read
that before touching the routers again.

**Read on your skill level:** you're comfortable with Pydantic validation patterns and SQLModel
table definitions, and the routers show you've internalized the CRUD-per-resource pattern
(`APIRouter(prefix=..., tags=...)`, consistent verb/path shapes). Where the gaps still are:
wiring layers together end-to-end (package imports, DB session dependency injection,
`main.py` → routers → crud → models) rather than any single file in isolation. That's what the
build order below is sequenced around — get one resource fully working end-to-end before
copying the pattern to the other two.

---

## Decision 1 — Unblock the package (do this first, it's a 30-second fix)

Empty `app/__init__.py`. Right now it contains a single stray character (`s`) that raises a
`NameError` the instant anything imports `app`. This isn't a design decision, just a fix — but
it's blocking literally everything else, including testing any other fix in this document.

## Decision 2 — Fix the two remaining model issues before building CRUD on top

Both are in `models/order.py`, both verified by actually importing the model:

- `__tablename__="orders"` needs to be a normal class-body assignment, not a class keyword
  argument — SQLModel/SQLAlchemy doesn't read `__tablename__` from class kwargs, so it's
  currently ignored and the table is named `order` (reserved SQL word):
  ```python
  class Order(SQLModel, table=True):
      __tablename__ = "orders"
  ```
- Rename `user_id` → `client_id` in both `models/order.py` and `schema/order.py` — there's no
  `User` model, the foreign key targets `Client`, and this name will otherwise leak into every
  router request body and response for orders.

Also still true from the last model audit and worth deciding now rather than after CRUD is
built: an `Order` with only `total: float` can't tell you *what* was sold. If you want the
inventory system to actually answer "what did this client order," you need an `OrderItem` link
table (order ↔ product, quantity, unit-price-at-time-of-sale) before `orders.py`'s create
endpoint is meaningful. Worth deciding now — retrofitting line items after routers/CRUD exist
means touching the schema, model, and router all at once instead of once.

## Decision 3 — Routers and CRUD: get one resource working end-to-end first

Don't fix all three routers in parallel — get `clients` fully working (schema → router →
`get_session` dependency → `crud/client.py` → real DB round-trip → visible in `/docs`) before
touching `orders.py`/`products.py`. It's easier to debug one working example than three
half-wired ones at once, and `clients.py` is already the most complete of the three (it's the
only router that correctly type-hints its request bodies).

Concretely, in order:
1. Build the session dependency: `app/database.py` (or `app/core/database.py`) with an
   `engine` and a `get_session()` generator, `Depends`-injected into router signatures. Nothing
   currently exists here.
2. Implement `crud/client.py`: plain functions taking a `Session` + args, returning models. No
   FastAPI imports in this layer — keeps it testable without the app running.
3. Wire `clients.py`'s five endpoints to that CRUD layer. Add `response_model=` to each (none
   currently declare one), add 404 handling for get/update/delete-by-id.
4. Remove the stray `app = FastAPI()` left inside `clients.py` — that instance belongs in
   `main.py`, not a router module.
5. Once `clients` works end-to-end, copy the pattern to `products.py` and `orders.py` — but
   first fix `products.py`'s missing `@router.get("/")` decorator (the route currently isn't
   registered at all) and add the missing `product`/`order` body parameters to the
   create/update endpoints in both files (currently they take no body, so there's no way to
   send data to them).
6. Wire `app/main.py`: instantiate `FastAPI()`, `include_router()` each resource, confirm all
   routes show up in `/docs`.

This is also the right stage to add **filtering** on list endpoints, since it was a stated
requirement: a `FilterParams` dependency per resource (e.g. `ProductFilterParams` with
`category`, `min_price`, `max_price`, `search`, pagination `limit`/`offset`), built with
SQLModel's `select()` + conditional `.where()` clauses. A handful of explicit, typed filter
params per endpoint beats a generic "filter anything" system at this project's size.

## Decision 4 — Cloud connectivity

Unchanged from the last audit, still two separate concerns:
1. **Database**: Postgres is local via docker-compose. For a cloud target, a managed Postgres
   (Neon, Supabase, Railway, or RDS) is the lowest-friction path — swap the connection string
   via environment variable once `core/config.py`/`database.py` reads `DATABASE_URL` from env
   instead of hardcoding it.
2. **App hosting**: deploy the FastAPI app somewhere (Railway, Fly.io, Render, or a container on
   AWS/GCP). Pick based on what you want exposure to — Fly.io/Railway for staying close to
   Docker, AWS (ECS/App Runner) if you want cloud-provider experience for a resume.

Get `.env` + `pydantic-settings` wired now, even while running locally — retrofitting config
management after hardcoding a local connection string is annoying later.

## Decision 5 — Auth

`schema/client.py` already defines `ClientLogin` (email + password), and `ClientCreate`
validates a minimum password length, but `crud/client.py` is empty (no hashing utility exists
anywhere) and `routers/auth.py` is a completely empty file. This needs, in order: a password
hashing function in the client CRUD layer (e.g. `passlib`/`bcrypt`), a login endpoint in
`auth.py` that verifies credentials and issues a session/JWT, and a dependency other routers can
use to require authentication. Build this after `clients.py` CRUD works, since login depends on
clients already being persistable.

## Decision 6 — AI-powered SQL analysis (the interesting/risky part, unchanged from last audit)

Still the feature most likely to go wrong if built naively — `routers/analytics.py` is still an
empty file, correctly left for last.

**The core risk:** letting an LLM write arbitrary SQL and executing it directly against your
database is one prompt injection or hallucination away from a `DELETE`/`DROP`, or from leaking
data outside intended scope. Treat model output like untrusted user input.

Recommended architecture, unchanged:
1. **Read-only DB role** — a Postgres role (`GRANT SELECT ONLY`) used exclusively by this
   feature. Never let generated SQL run under a role that can write.
2. **Schema-scoped prompting** — give the model your actual table/column definitions, not the
   whole DB, in the system prompt.
3. **Validate before executing** — parse the generated SQL (e.g. `sqlglot`) and assert it's a
   single `SELECT` touching only allow-listed tables before running it. Reject anything else
   outright.
4. **Row/result limits** — inject a `LIMIT` if the model didn't include one, cap execution time
   (`statement_timeout`).
5. **Show the user the generated SQL**, not just the answer — trust feature and debugging aid.

Suggested flow: `POST /analytics/ask` → build prompt with schema + question → call LLM →
validate SQL → execute against the read-only connection → return `{sql, columns, rows}`.

## Suggested build order (supersedes the previous version's list)

1. Empty `app/__init__.py` (Decision 1).
2. Fix `models/order.py`'s `__tablename__` and `user_id`→`client_id` (Decision 2). Decide on
   `OrderItem` line items now if you want orders to be meaningful.
3. Build `database.py` (engine + `get_session()`), delete `src/inventory_system` if it's still
   around.
4. Alembic init, first migration, confirm it applies against the docker-compose Postgres.
5. `crud/client.py`, wire `clients.py` end-to-end (session, response_model, 404s), confirm in
   `/docs`. Remove the stray `FastAPI()` from `clients.py` while you're in the file.
6. Fix `products.py`'s missing decorator and both routers' missing request-body params, then
   repeat step 5's pattern for `crud/order.py`/`crud/product.py` and their routers.
7. Wire `app/main.py`: real `FastAPI()` instance, `include_router()` for everything.
8. Filtering params on list endpoints.
9. Auth: password hashing in `crud/client.py`, login endpoint in `auth.py`.
10. Deploy to a cloud Postgres + hosted app, confirm it works end-to-end remotely.
11. AI/SQL analysis feature, with the guardrails in Decision 6.
12. Tests (the `test/` dir is still empty).

Come back at any decision point above where you want a second opinion before committing.
