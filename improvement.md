# Improvement Plan — Madre Tierra Inventory System

## Where things stand right now

This is an honest read of the repo as it exists today, not a criticism — you're early, and that's the right time to fix direction.

**What's there:**
- Two parallel skeletons: `src/inventory_system/` (a `uv`-managed package with just a `main()` stub) and `Madre_Tierra_Inventory_System/app/` (the real FastAPI app: `models/`, `crud/`, `routers/`). Only one of these should survive.
- `docker-compose.yaml` runs Postgres 16 — good, that's a real decision already made.
- `pyproject.toml` is small and deliberate (sqlmodel, pydantic, phonenumbers). `requirements.txt` is 90 lines and includes things never imported anywhere (`nicegui`, `pandas`, `numpy`, `altair`, `pydeck`, `streamlit`-adjacent packages, `alembic`). That file looks like a `pip freeze` from a broader environment, not a curated dependency list for this project.
- `models/client.py` is solid: SQLModel table, validated email/phone, a `field_validator` normalizing email casing.
- `models/order.py` has a syntax error (`client: Client | None Relationship(...)` — missing `=`), a `back_populates` mismatch (`"Orders"` vs the actual attribute `orders`), and imports `from models import Client` which won't resolve without a package `__init__.py` re-export.
- `models/product.py`, `crud/main.py`, `crud/database.py`, `app/main.py`, all `__init__.py` files, and `routers/` are empty.
- No `.env` / settings module, no Alembic migration setup (despite being in requirements), no tests, no API routes yet, no README/DOCUMENTATION content describing the actual app (DOCUMENTATION.md is a 6-line technology-flow note).

**Read on your skill level:** you're comfortable with Pydantic validation patterns and SQLModel table definitions, and you've already made a real infra decision (dockerized Postgres). Where you're less certain: multi-file/package import structure, relationship wiring between models, and how the pieces (models → CRUD → routes → deployment) fit together end to end. That's exactly what this plan is structured around.

---

## Decision 1 — Pick one project skeleton

Delete `src/inventory_system/`. Keep `Madre_Tierra_Inventory_System/app/`, but restructure it as an installable package so imports are unambiguous:

```
madre_tierra/
  app/
    __init__.py
    main.py              # FastAPI() instance, includes routers
    core/
      config.py          # Settings (pydantic-settings), reads .env
      database.py        # engine, SessionDep
    models/
      __init__.py
      client.py
      product.py
      order.py
    schemas/             # Pydantic request/response models, separate from table models
      client.py
      product.py
      order.py
    crud/
      client.py
      product.py
      order.py
    routers/
      clients.py
      products.py
      orders.py
      analytics.py       # the AI/SQL feature lives here
    ai/
      sql_agent.py        # prompt building, guardrails, execution
  alembic/
    versions/
  tests/
  .env.example
  pyproject.toml
```

One `pyproject.toml` at the root, `uv` for dependency management (drop `requirements.txt` entirely — regenerate it only if some deployment target strictly needs it, via `uv export`).

**Why separate `models/` from `schemas/`:** your table models (SQLModel) define what's in Postgres. Your API shouldn't always accept/return the exact same shape (e.g., you don't want clients able to set `id` on create, or you may want to hide internal fields). Keeping schemas separate is a small amount of extra typing now that saves you from painful refactors once you add auth or computed fields.

## Decision 2 — Fix the models before building anything on top

Concrete fixes needed in `order.py`:
- `client: Client | None = Relationship(back_populates="orders")` (add the `=`, fix the string to match `Client.orders`)
- Rename `user_id` to `client_id` for consistency with the `Client` model, or rename consistently — pick one term (`client` seems right given the domain) and use it everywhere.
- `product.py` is empty — this is your core inventory entity. Minimum fields: `id`, `sku`, `name`, `description`, `quantity`, `unit_price`, `category`, `created_at`, `updated_at`. Think about whether quantity changes should be tracked as an audit log (a `StockMovement` table) rather than just overwriting a number — for an inventory system, "what changed and why" is often the actual point. I'd recommend adding that table now rather than bolting it on later, but it's your call.
- You'll need an `OrderItem` link table (order ↔ product, many-to-many with quantity/price-at-time-of-sale) since an `Order` with just a `total: float` and no line items can't tell you *what* was sold.

I'd suggest you write these three files yourself now that the gaps are named — ping me if the relationship syntax or the link-table pattern isn't clicking.

## Decision 3 — CRUD and routing layers

Standard layering, thin on top of SQLModel:
- `crud/*.py`: plain functions taking a `Session` and args, returning models. No FastAPI imports here — keeps this layer testable without spinning up the app.
- `routers/*.py`: FastAPI path operations, dependency-inject the `Session`, call `crud`, translate to `schemas` for the response.

This is a good stage to introduce **filtering**, since you mentioned it as a requirement. Recommended pattern: a shared `FilterParams` dependency per resource (e.g. `ProductFilterParams` with `category`, `min_price`, `max_price`, `in_stock`, `search`, pagination `limit`/`offset`), built with SQLModel's `select()` + conditional `.where()` clauses. Don't build a generic "filter anything" system — that's over-engineering for a learning project; a handful of explicit, well-typed filter params per endpoint is more maintainable and easier to reason about.

## Decision 4 — Cloud connectivity

Two separate concerns here, don't conflate them:
1. **Database**: your Postgres is local via docker-compose. For "connect to a cloud service," the lowest-friction path is a managed Postgres (Neon, Supabase, Railway, or RDS if you want AWS exposure) — swap the connection string via environment variable, no code changes needed if `core/config.py` reads `DATABASE_URL` from env rather than hardcoding.
2. **App hosting**: deploy the FastAPI app itself somewhere (Railway, Fly.io, Render, or a container on AWS/GCP). Given you're doing this to learn, I'd pick based on what you want exposure to — Fly.io/Railway if you want to stay close to Docker; AWS (ECS or App Runner) if you want cloud-provider experience that transfers to a resume.

Tell me which direction interests you more (resume-building AWS exposure vs. fastest path to "it's live") and I can help you scope that step when you get there — this is exactly the kind of fork where I'd want your input rather than picking for you.

Either way: get `.env` + `pydantic-settings` wired now, even while running locally. Retrofitting config management after you've hardcoded a local connection string is annoying.

## Decision 5 — AI-powered SQL analysis (the interesting/risky part)

This is the feature most likely to go wrong if built naively, so slow down here specifically.

**The core risk:** if you let an LLM write arbitrary SQL and you execute it directly against your production database, you're one prompt injection or hallucination away from a `DELETE` or `DROP`, or from leaking data outside the tenant/company scope. This is a real, well-known failure mode — treat it like accepting user input, because that's what it is.

Recommended architecture:
1. **Read-only DB role.** Create a Postgres role (`GRANT SELECT ONLY`) used exclusively by the AI analysis feature. Never let generated SQL run under a role that can write.
2. **Schema-scoped prompting.** Give the model your actual table/column definitions (not the whole DB) in the system prompt, so it writes queries against real columns instead of guessing.
3. **Validate before executing.** Parse the generated SQL (e.g. with `sqlglot`) and assert it's a single `SELECT` statement touching only allow-listed tables, before running it. Reject anything else outright — don't try to "sanitize" a write statement into a read one.
4. **Row/result limits.** Always inject a `LIMIT` if the model didn't include one, and cap execution time (Postgres `statement_timeout`).
5. **Show the user the generated SQL**, not just the answer — this is both a trust feature and a debugging aid for you while developing.

Suggested flow: `POST /analytics/ask` → build prompt with schema + user's natural-language question → call LLM → validate SQL → execute against read-only connection → return `{sql, columns, rows}` to the frontend.

This is a good candidate to build *last*, after CRUD and filtering work, since it depends on having real data and a stable schema to describe to the model.

## Suggested build order

1. Fix `order.py`, write `product.py`, decide on the `OrderItem` / `StockMovement` tables.
2. Wire `core/config.py` + `core/database.py` (engine, session dependency), delete `src/inventory_system`.
3. Alembic init, first migration, confirm it applies against the docker-compose Postgres.
4. CRUD layer for clients/products/orders (no HTTP yet — test these as plain Python/pytest).
5. Routers + schemas, get full CRUD reachable over HTTP, verify in `/docs`.
6. Filtering params on list endpoints.
7. Deploy to a cloud Postgres + hosted app, confirm it works end-to-end remotely.
8. AI/SQL analysis feature, with the guardrails above.
9. Tests you didn't already write inline (the empty `test/` dir), basic auth if this will ever be multi-user.

Come back to me at any decision point above where you want a second opinion before committing — that's the "guidance when uncertain" role you asked for, not a request for me to write the features myself.
