# Phase 4 — Prove the full stack works, end to end, for `clients`

**Why `clients` specifically:** it's the most complete resource already (schemas, CRUD, and a
real service layer exist for it), so it's the cheapest path to one fully working vertical slice
— a proven template (session handling, service calls, response models, error handling) to copy
for `orders`/`products`.

**Status as of 2026-08-31: not started.** All five endpoints in `routers/clients.py` are still
bare `pass` bodies.

## Checklist

- [ ] Wire `app/routers/clients.py`: inject `get_session()`, call into `client_service` for each
      of the five endpoints, add 404 handling for the "not found" exceptions.
- [ ] Fix `update_client`'s `response_model=ClientUpdate` → `response_model=ClientRead`
      (`ClientUpdate` is all-optional with no `id` — the wrong shape for what an update endpoint
      returns). Still present, unchanged.
- [x] `app/main.py` now has a real `FastAPI()` instance and calls
      `app.include_router(api_router)` — **but** the import is `from routers import api_router`,
      which will fail once `main.py` is actually run as part of the `app` package (should be
      `from app.routers import api_router`, matching how every other file in this project
      imports). Fix this import before relying on `main.py` working.
- [ ] Confirm in `/docs` by actually creating, reading, updating, and deleting a client through
      the browser — not just reading the code.

## Done when

You can create, read, update, delete, and search a client through `/docs` against the real
database, including a clean 404 on a missing client.
