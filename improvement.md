# Improvement Plan — Madre Tierra Inventory System

_Last audited: 2026-08-19. This replaces the previous version of this file (audited 2026-08-09),
which is now stale — some of what it flagged is genuinely fixed, some commit messages claimed
fixes that didn't fully land, and one new critical bug was introduced along the way. Treat this
as the current source of truth. `Madre_Tierra_Inventory_System/app/models/EVALUATION.md` and
`Madre_Tierra_Inventory_System/app/routers/EVALUATION.md` are now historical snapshots from the
08-09 audit — useful for context, but don't trust their bullet points as current state without
re-checking against the file itself._

## Where things stand right now

**Real progress since the last audit:** `Order.__tablename__` is now a proper class-body
assignment (fixed), `back_populates` matches on both sides (`client` ↔ `orders`, fixed),
`user_id` → `client_id` is done in both the model and schema (fixed), `products.py`'s missing
`@` decorator is fixed, the stray `FastAPI()` instance is gone from `clients.py`. A whole new
`app/service/` layer and `app/core/security.py` (Argon2 password hashing) were added — a good,
professional instinct (business logic like "email already registered" and password hashing
don't belong in routers or raw CRUD).

**The architecture itself is sound and doesn't need to change:** `schema` → `service` → `crud` →
`models`, with `core` for cross-cutting utilities, is exactly how a real FastAPI codebase is
organized. Every problem below is about finishing/wiring/testing, not about restructuring.

**Verified by actually running the code, not just reading it** (including reproducing a bug that
only shows up when the ORM is actually used, not at import time):

- `app/__init__.py` still contains only the stray `s` — `import app` raises `NameError`,
  blocking every router, model, and the app itself. **Still the #1 fix**, unchanged from every
  previous audit.
- `app/main.py` is still empty — no `FastAPI()`, no `include_router()`. Nothing for `uvicorn` to
  serve even once imports work.
- `app/database.py` is still fully commented out — no `engine`, no `get_session()`. This is why
  every CRUD/service function's `Session` parameter has nothing to supply it.
- **New, critical, confirmed-by-running-it:** `models/client.py` and `models/order.py` import
  each other and mix forward-reference styles (`client.py` uses a quoted string, `order.py` uses
  a direct `client.Client | None` reference). Plain `import` happens to succeed today only
  because this project targets Python 3.14, which defers annotation evaluation by default (PEP
  649) — on any earlier Python this would raise `AttributeError` depending on import order.
  **But even on 3.14, the first time SQLAlchemy actually configures the mappers (which happens
  automatically on the first real query), it crashes:**
  ```
  AttributeError: 'Table' object has no attribute 'Client | None'
  ```
  This will break the very first request that touches client/order data once CRUD is wired up —
  see Decision 2 for the verified fix.
- `client_service.py` cannot currently be imported: it imports `ClientNotFoundErrorById`, but
  the class is actually named `ClientNotFoundByIdError` (`ImportError`), and the file ends
  mid-statement (`def retriev`) — a real `SyntaxError`.
- `Client` (the DB model) has no password/`hashed_password` field at all. `security.py`'s
  hashing utility and `ClientLogin`/`ClientCreate.password` exist, but there's nowhere to
  persist a hash yet.
- Every router endpoint across all three resources is still `pass` — none call into
  `service`/`crud`.

Full router- and model-specific detail from the 08-09 audit is still mostly accurate for what it
covered; this file adds what's changed and what's new since.

**Completion estimate (this pass):** roughly 25–30% of a working, deployable app. The layering
(`schema → service → crud → models`, `core` for cross-cutting concerns) is correct and doesn't
need to change — but `app/__init__.py`'s stray `s` currently means nothing below can even be
imported, let alone run:

| Layer | Estimate | Note |
|---|---|---|
| Models | ~85% | fields correct; `Client`↔`Order` cross-import crashes on first real query (Decision 2) |
| Schemas | ~80% | `OrderRead.created_at` type bug, `ClientSearchParams.phone_number` still required (Decision 6) |
| CRUD | ~70% | client/order/product basic ops correct; new `search_client` bug found this pass (below) |
| Service layer | ~30% | `client_service.py` mostly wired but has 2 new bugs found this pass (below); order/product services are empty stubs |
| Routers | ~35% | schemas correctly type-hinted on `clients.py`; every endpoint body is `pass`; no session dependency anywhere; `auth.py`/`analytics.py` are 0 bytes |
| Core infra (`__init__.py`, `main.py`, `database.py`) | 0% | the actual blocker — nothing runs until this is fixed |
| Auth | ~15% | hashing utility works in isolation; no `hashed_password` column, no login endpoint |
| Tests | 0% | no `tests/` directory anywhere |
| Deploy | 0% | only local Postgres via docker-compose |

**Two new bugs found this pass** (verified by reading, not yet run against a live DB):

- `app/crud/client.py:65` — `search_client`'s `phone_number` filter is copy-pasted wrong:
  ```python
  query = query.where(Client.phone_number.ilike(f"%{params.email}%"))
  ```
  It filters the `phone_number` column against `params.email` instead of `params.phone_number` —
  searching by phone will silently return wrong (or no) results. Fix: use `params.phone_number`.
- `app/service/client_service.py:45-49` — `update_client_service` has two bugs stacked:
  ```python
  def update_client_service(session, client_id, client_new_data_in) -> list[ClientRead]:
      try:
          update_client(session, client_id, client_new_data_in)   # missing `return`
      except NoResultFound as e:
          raise ClientNotFoundForUpdate()   # constructor requires (client_id, client_new_data)
  ```
  The success path discards the updated client and implicitly returns `None`, breaking the
  declared `-> list[ClientRead]` contract. The failure path itself raises `TypeError` because
  `ClientNotFoundForUpdate.__init__` requires two positional args that aren't passed here.

Also verified independently this pass (isolated `uv` venv, no project files modified): the
`Client`↔`Order` mapper crash from Decision 2 reproduces exactly as described
(`AttributeError: 'Table' object has no attribute 'Client | None'`), and a fresh `uv sync` does
*not* install `argon2`, confirming Decision 7's `argon2-cffi` gap is real, not theoretical.

---

## Decision 1 — Unblock the package (still first, still a 30-second fix)

Empty `app/__init__.py`. Nothing else here can be verified end-to-end until this is fixed —
this has now been the top blocker across three audits.

## Decision 2 — Fix the `Client`↔`Order` relationship (new, verified)

Don't cross-import the two model modules at all — import one direction only, and use a plain
quoted class name (not a module-qualified reference, and not a fully-quoted `"Client | None"`,
which I also confirmed fails the same way). Verified working by actually calling
`sqlalchemy.orm.configure_mappers()`:

```python
# models/order.py
from typing import Optional
from app.models.client import Client

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    ...
    client: Optional["Client"] = Relationship(back_populates="orders")
```

```python
# models/client.py — no import of order.py needed
class Client(SQLModel, table=True):
    ...
    orders: list["Order"] = Relationship(back_populates="client")
```

Do this before building more CRUD/service logic on top of these models — right now it's a
silent time bomb that only goes off on first real use.

## Decision 3 — Add password storage to `Client`

`models/client.py` needs a `hashed_password: str` field before `register_client()` in the
service layer can work at all — right now there's no column to put the Argon2 hash into. Add it
as a plain non-indexed string column; never store or return the plaintext `password` from
`ClientCreate` beyond the point where it's hashed.

## Decision 4 — Fix the service layer

In `client_service.py`:
1. Fix the import: `ClientNotFoundErrorById` → `ClientNotFoundByIdError`.
2. Finish (or remove) the truncated `def retriev` function — it's currently a syntax error.
3. `register_client()` currently builds `ClientCreate(..., hashed_password=...)` — `ClientCreate`
   has no `hashed_password` field (silently dropped) and the call omits the required `password`
   field, so it raises a validation error the moment it runs. It should build a `Client(...)`
   (the table model, once Decision 3 lands), not another `ClientCreate`.
4. `retrieve_client_by_id`/`retrieve_client_by_email` catch `NoResultFound`, but the CRUD
   functions they call return `None` on a miss, never raise. Either change the CRUD layer to
   raise, or change the service layer to check for `None` and raise the custom exception itself
   — right now a missing client silently returns `None` instead of the intended 404-shaped error.
5. Replace `from app.models.client import *` / `from app.crud.client import *` with explicit
   imports — works today only via transitive re-export and makes it unclear where names come
   from.
6. `update_client_service` is missing a `return` before its call to `update_client(...)` — the
   success path currently discards the updated client and implicitly returns `None`, breaking
   its declared `-> list[ClientRead]` contract. Its `except` block also calls
   `ClientNotFoundForUpdate()` with no arguments, but that exception's `__init__` requires
   `(client_id, client_new_data)` — this raises `TypeError` instead of the intended custom
   error. Fix both: add the `return`, and pass the required args (or give the exception
   defaults) when raising. Same root cause as point 4 above — this crud/service pair needs a
   consistent "not found" story.

Then extend the same pattern to `order_service.py`/`product_service.py`, currently empty stubs.

## Decision 5 — Routers and CRUD: get one resource working end-to-end first

Still the right call to do `clients` fully before `orders`/`products`, per the last audit. Fix
these router-specific bugs while wiring:

- `orders.py`: `create_order()` takes no body parameter at all and doesn't import `OrderCreate`
  — there's no way to send data to it.
- `orders.py`: `update_order(order_id: int, client: ClientUpdate)` — typed with `ClientUpdate`
  instead of `OrderUpdate`. Looks like a copy-paste from `clients.py` that was never corrected.
- `products.py`: still no `DELETE /{product_id}` (inconsistent with the other two resources);
  `create_product`/`update_product` still take no body parameter and don't import
  `ProductCreate`/`ProductUpdate`.
- `clients.py`: `update_client`'s `response_model=ClientUpdate` should be `ClientRead` —
  `ClientUpdate` is all-optional and has no `id`, the wrong shape for what an update endpoint
  returns.
- `auth.py`, `analytics.py` are still 0 bytes — not even an `APIRouter()` instance.

Concretely, in order:
1. Build `database.py` — `engine` + `get_session()`, `Depends`-injected into router signatures.
2. Wire `clients.py`'s five endpoints to `client_service`/`crud/client.py`, add 404 handling
   where the service layer returns/raises "not found."
3. Once `clients` works end-to-end and shows correctly in `/docs`, fix and repeat the pattern
   for `orders.py`/`products.py`, fixing the bugs listed above along the way.
4. Wire `app/main.py`: instantiate `FastAPI()`, `include_router()` each resource.

This is also the right stage to add **filtering** on list endpoints (a stated requirement): a
`FilterParams` dependency per resource built with SQLModel's `select()` + conditional `.where()`
clauses.

## Decision 6 — Schema fixes

- `schema/client.py`: `ClientSeachParams` (typo: "Seach") inherits `ClientBase`, which makes
  `phone_number` a **required** field on what should be an all-optional filter object — only
  `name`/`email` were overridden as optional. Fix the typo and make every field optional.
- `schema/order.py`: `OrderRead.created_at: str` but the model field is `datetime`. Pydantic v2
  does not coerce `datetime` → `str` for a plain `str` field — this will raise a response
  validation error the first time an order is returned. Change to `datetime`.
- `crud/client.py:65` — `search_client`'s `phone_number` filter is copy-pasted wrong:
  `Client.phone_number.ilike(f"%{params.email}%")` filters the phone column against
  `params.email` instead of `params.phone_number`. Searching by phone will silently return
  wrong (or no) results. Fix: use `params.phone_number`.

## Decision 7 — Dependency management, config, and repo hygiene

- `pyproject.toml` (6 deps, backing `uv.lock`) and `requirements.txt` (58 packages, including
  `nicegui`, `pandas`, `pyarrow`, `altair`, `pydeck`, `GitPython` — clearly a dump of an
  unrelated broader environment) are out of sync. Since `uv.lock` exists, `pyproject.toml` is
  the real source of truth — drop `requirements.txt`, or regenerate it with `uv export` only
  right before a deploy that specifically needs it.
- Add to `pyproject.toml`: `argon2-cffi` (used in `core/security.py` but not declared — a fresh
  `uv sync` won't install it), a Postgres driver matching `.env`'s connection string
  (`psycopg2-binary`), and `pydantic-settings` once config-from-env is wired (see Decision 8).
- `.env` is committed to git and not in `.gitignore`. Current value is a placeholder
  (`<root>:<root>`), so nothing sensitive has leaked yet, but the pattern is dangerous the moment
  a real credential goes in. Add `.env` to `.gitignore` now and commit a `.env.example` instead.
- `.claude/worktrees/bridge-cse_...` is an empty directory tracked in git, unrelated to the app —
  looks accidental; worth reviewing what's actually meant to be tracked under `.claude/`.
- No `tests/` directory exists anywhere. Nearly every bug in this file (broken imports, a wrong
  schema type, an unregistered route, a truncated function) is exactly what a one-file smoke
  test (`from app.main import app`, then `TestClient` hitting each router) would have caught the
  moment it landed instead of on the next manual audit. Worth adding early, not at the end.

## Decision 8 — Cloud connectivity

Unchanged from previous audits, still two separate concerns:
1. **Database**: Postgres is local via docker-compose. For a cloud target, a managed Postgres
   (Neon, Supabase, Railway, or RDS) is the lowest-friction path — swap the connection string via
   environment variable once `database.py` reads `DATABASE_URL` from env (via
   `pydantic-settings`) instead of a hardcoded/commented-out string.
2. **App hosting**: deploy the FastAPI app somewhere (Railway, Fly.io, Render, or a container on
   AWS/GCP). Pick based on what you want exposure to.

## Decision 9 — Auth

Now blocked on Decisions 3 and 4 rather than being fully unstarted: `Client` needs the
`hashed_password` column, `client_service.register_client` needs to actually work, and then
`routers/auth.py` needs a login endpoint that calls `retrieve_client_by_email` +
`verify_password`, plus a dependency other routers can use to require authentication.

## Decision 10 — AI-powered SQL analysis (unchanged, still the highest-risk part)

`routers/analytics.py` is still empty, correctly left for last.

**The core risk:** letting an LLM write arbitrary SQL and executing it directly against your
database is one prompt injection or hallucination away from a `DELETE`/`DROP`, or from leaking
data outside intended scope. Treat model output like untrusted user input.

Recommended architecture, unchanged:
1. **Read-only DB role** — a Postgres role (`GRANT SELECT ONLY`) used exclusively by this
   feature. Never let generated SQL run under a role that can write.
2. **Schema-scoped prompting** — give the model your actual table/column definitions, not the
   whole DB, in the system prompt.
3. **Validate before executing** — parse the generated SQL (e.g. `sqlglot`) and assert it's a
   single `SELECT` touching only allow-listed tables before running it. Reject anything else.
4. **Row/result limits** — inject a `LIMIT` if the model didn't include one, cap execution time
   (`statement_timeout`).
5. **Show the user the generated SQL**, not just the answer — trust feature and debugging aid.

Suggested flow: `POST /analytics/ask` → build prompt with schema + question → call LLM →
validate SQL → execute against the read-only connection → return `{sql, columns, rows}`.

---

## Guided build order — what to work on first, and why

This is the order to actually do the work in, start to finish, with the reasoning behind each
step so the sequence isn't arbitrary. The rule underneath all of it: **fix things in the order
that unblocks verification, not in the order they feel important.** A bug you can't observe
(because the app can't even import yet) is a bug you can't confirm you've fixed — so everything
below is sequenced to get you to a runnable, testable state as fast as possible, then build
outward from one fully-working resource instead of half-wiring three at once.

### Phase 1 — Make the app importable at all

1. **Empty `app/__init__.py`** (Decision 1). This is a 30-second fix but it's the reason nothing
   else in this project can be verified end-to-end right now — `import app` currently raises
   `NameError` before a single router, model, or test can run. Do this literally first.
2. **Fix the `Client`↔`Order` relationship** (Decision 2). Do this immediately after, before
   writing or fixing any CRUD/service code that touches either model. It's not a bug that shows
   up on import — it's a silent time bomb that only detonates the first time SQLAlchemy
   configures its mappers (the first real query), which is exactly the moment you'd otherwise be
   in the middle of testing something else and lose time misdiagnosing a relationship bug as
   something in the code you just wrote.

**Why this phase first:** every other phase involves running code to check it works. Until
imports succeed and the models can be mapped, "does this work" isn't answerable — you'd be
debugging blind.

### Phase 2 — Give the app somewhere to persist data

3. **Add `hashed_password` to `Client`** (Decision 3). Small, but it's a hard dependency for
   Phase 3 — there's no column to write the Argon2 hash into otherwise.
4. **Build `database.py`** — `engine` + `get_session()` (Decision 5) — and add the missing
   `psycopg2-binary`/`argon2-cffi` to `pyproject.toml` (Decision 7) so a fresh `uv sync` actually
   installs what the code imports.
5. **Alembic init + first migration**, confirmed applying against the docker-compose Postgres.

**Why now, before routers:** routers and services both depend on a working `Session`. Building
the session dependency before wiring any endpoint means you wire each endpoint once, correctly,
instead of stubbing it now and coming back to inject the session later. Migrations come right
after the engine because you want the *first* time you apply a migration to be against a small,
simple schema — not after three resources' worth of models have accumulated changes.

### Phase 3 — Get the business logic right for one resource

6. **Fix `client_service.py`** completely (Decision 4, including the two bugs found in the
   2026-08-19 second pass: `update_client_service`'s missing `return` and the
   `ClientNotFoundForUpdate()` call missing its required args). Also fix `crud/client.py`'s
   `search_client` phone-filter bug (Decision 6) while you're in this file.

**Why service logic before routers:** the router layer should be thin — parse the request, call
the service, shape the response. If the service layer underneath is still buggy, wiring the
router just gives you a working-looking endpoint that returns wrong data or throws on the
not-found path. Fixing `client_service.py` fully first means Phase 4's router work is just
plumbing, not debugging.

### Phase 4 — Prove the full stack works, end to end, for one resource

7. **Wire `clients.py`** — inject `get_session()`, call into `client_service`, set correct
   `response_model`s (including the `ClientUpdate`→`ClientRead` fix from Decision 5), add 404
   handling for the "not found" exceptions. Confirm it in `/docs` by actually creating, reading,
   updating, and deleting a client.
8. **Wire `app/main.py`** just enough to serve this one router — real `FastAPI()` instance,
   `include_router(clients_router)`.

**Why clients specifically, and why prove it fully before moving on:** `clients` is the most
complete resource already (schemas, CRUD, and a real service layer exist for it), so it's the
cheapest path to a fully working vertical slice. Once one resource works end-to-end and you've
actually clicked through `/docs`, you have a proven template — session handling, service calls,
response models, error handling — to copy for the other two. Debugging one working example is
far cheaper than debugging three half-wired resources simultaneously, where a bug in the shared
session dependency looks like three separate bugs.

### Phase 5 — Repeat the proven pattern for the remaining resources

9. **Fix `orders.py`/`products.py`'s router bugs while wiring them**: missing body parameters on
   `create_order`/`update_order`/`create_product`/`update_product`, the
   `update_order(order_id, client: ClientUpdate)` copy-paste typo, and the missing
   `DELETE /products/{id}` (decide deliberately whether products should hard-delete at all).
   Fix `OrderRead.created_at`'s `str`→`datetime` type bug and `ClientSearchParams`'s
   still-required `phone_number` (Decision 6) along the way.
10. Build out `order_service.py`/`product_service.py` following the same shape as
    `client_service.py` (now that it's a correct reference).
11. **Extend `include_router()`** in `main.py` to cover `orders` and `products`.

**Why not do all three resources in parallel from the start:** by this point the pattern is
proven and the remaining work is almost entirely repetition of Phase 3+4 plus fixing the
specific, already-catalogued bugs in each file — low-risk, high-speed work instead of design
work.

### Phase 6 — Lock in correctness with a safety net

12. **Add the one-file smoke test** (Decision 7): `from app.main import app`, then a
    `TestClient` hitting every router's CRUD cycle. Every bug catalogued in this document —
    broken imports, a wrong schema type, an unregistered route, a truncated function, the two
    bugs found this pass — is exactly the class of thing this single test file would catch
    immediately instead of on the next manual audit.

**Why here and not earlier or later:** too early, and there's nothing working yet to test
meaningfully. Too late (e.g. after auth and deploy), and you'll have shipped further bugs of the
same shape without a net. Right after all three resources work is the point of maximum leverage
— you're about to start touching auth and cross-cutting concerns, which is exactly when a
regression in "does GET /clients still work" is easiest to introduce and hardest to notice by
eye.

### Phase 7 — Round out what a real API needs

13. **Filtering params on list endpoints** for `orders`/`products`, matching the pattern already
    started for `clients` via `ClientSearchParams`.
14. **Auth**: `routers/auth.py` login endpoint calling `retrieve_client_by_email_service` +
    `verify_password`, plus a dependency other routers can use to require authentication
    (Decision 9).

**Why auth this late, not earlier:** it was genuinely blocked until now — it needs a working
`hashed_password` column (Phase 2) and a working, bug-free `client_service` (Phase 3) to check
credentials against. Doing it earlier would mean building auth against a service layer you know
is still broken.

### Phase 8 — Get it out of your laptop

15. **Repo/config hygiene**: drop `requirements.txt` (or regenerate via `uv export` only when a
    deploy needs it), move `.env` values to `pydantic-settings`-driven config, commit a
    `.env.example` (Decision 7).
16. **Deploy**: managed Postgres (Neon/Supabase/Railway/RDS) + hosted app (Railway/Fly.io/Render/
    container), swapping the connection string via `DATABASE_URL` env var (Decision 8).

**Why deploy near the end, not the middle:** deploying earlier just means re-deploying every
time you fix the next layer's bugs — better to deploy once the API surface (all three resources
+ auth) is actually stable and tested locally, so the deploy step is validating infrastructure,
not chasing application bugs in a slower feedback loop.

### Phase 9 — The one deliberately-last feature

17. **AI-powered SQL analytics** (`routers/analytics.py`), with the guardrails in Decision 10:
    read-only DB role, schema-scoped prompting, SQL validation before execution, row/time limits,
    and surfacing the generated SQL to the user.

**Why last, on purpose:** this is the highest-risk feature in the project — letting a model
generate SQL that runs against your database is one hallucination or prompt injection away from
a destructive query. It also needs a stable, finished schema to describe to the model and real
data to be useful to test against. Building it earlier means building it twice: once against a
schema that's still changing, and again once it stabilizes.

---

Come back at any phase above where you want a second opinion before committing.
