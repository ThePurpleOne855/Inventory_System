# Phase 3 — Get the business logic right for `clients`

**Why service logic before routers:** the router layer should be thin — parse the request, call
the service, shape the response. If the service layer is still buggy, wiring the router just
gives you a working-looking endpoint that returns wrong data or throws on the not-found path.

## Checklist, in `app/service/client_service.py`

All items below are done and verified end-to-end against the live docker-compose Postgres
(not just read — actually executed, including a real duplicate-email collision test).

- [x] Fix the import: `ClientNotFoundErrorById` → `ClientNotFoundByIdError`.
- [x] Finish (or remove) the truncated `def retriev` function — gone.
- [x] `register_client_service()` builds `Client(...)` (the table model) with
      `hashed_password=hash_password(client_in.password)`, not `ClientCreate(...)`.
- [x] `retrieve_client_by_id_service`/`retrieve_client_by_email_service` — try/except replaced
      with explicit `None` checks:
      ```python
      def retrieve_client_by_id_service(session: Session, client_id: int) -> ClientRead:
          client = get_client_by_id(session, client_id)
          if client is None:
              raise ClientNotFoundByIdError(client_id)
          return client
      ```
      Same pattern for the by-email variant. Confirmed via `typing.get_type_hints()` that both
      resolve cleanly (this also caught the `EmailStr` issue below).
- [x] Wildcard imports replaced with explicit named imports from both `app.models.client` and
      `app.crud.client`; `from pydantic import EmailStr` added explicitly (the transitive
      re-export it relied on before is gone now that the crud wildcard import was removed —
      confirmed this would otherwise `NameError` at type-hint-resolution time, then confirmed the
      fix resolves cleanly).
- [x] `update_client_service` — `return` restored, `ClientNotFoundForUpdate(client_id,
      client_new_data_in)` called with its required args, return type corrected to `ClientRead`
      (it returns one client, not a list). Verified via a real duplicate-email update against
      Postgres — see `crud/client.py` below.
- [x] `search_client_service` — simplified to `return search_client(session, params)`, no
      exception handling. `search_client` returns a list, and an empty list is a valid search
      result, not a "not found" error — raising here would have been wrong REST behavior once
      wired to a router.

## Checklist, in `app/crud/client.py`

- [x] `search_client`'s phone-filter bug fixed: now correctly uses
      `Client.phone_number.ilike(f"%{params.phone_number}%")`.
- [x] `get_client_by_email`'s `Optinal[Client]` typo fixed to `Optional[Client]` — confirmed via
      `typing.get_type_hints()`, which would otherwise `NameError` (deferred-annotation
      evaluation on Python 3.14 hid this on plain import, but FastAPI's own introspection would
      have hit it eventually).
- [x] `update_client` hardened against a real race/UX case surfaced during this pass: updating a
      client's email to one already used by another client now raises a clean
      `ValueError("Email already registered to another client")` instead of a raw
      `IntegrityError` — wrapped in `try: session.commit() / except IntegrityError: session.rollback(); raise ValueError(...)`.
      Needed `from sqlalchemy.exc import IntegrityError` (an earlier attempt wrote
      `from sqlalchemy.exc.IntegrityError import IntegrityError`, which doesn't exist as a
      submodule path and broke the whole module — caught and fixed). Verified live: created two
      clients, updated one to the other's email, confirmed `ValueError` raised and the
      transaction rolled back correctly.
- [x] Leftover dead code (duplicate `commit()/refresh()/return` after the new
      `try/except`) removed.

## Checklist, in `app/schema/client.py`

- [x] `ClientSearchParams` typo fixed (`ClientSeachParams` → `ClientSearchParams`), and now
      `phone_number: Optional[PhoneNumber] = None` is added alongside `email`/`name`. Confirmed
      `ClientSearchParams()` constructs with zero arguments.

## Done when

`client_service.py` and `crud/client.py` import cleanly and every function
(`register_client_service`, `retrieve_client_by_id_service`, `retrieve_client_by_email_service`,
`search_client_service`, `update_client_service`) behaves correctly when called directly against
a real session — ✅ **all verified against the live docker-compose Postgres.** Phase 3 is
complete.

**One item surfaced during this pass that's out of scope for this file:** `app/crud/__init__.py`
still has its own pre-existing bug — `from .order import ..., delete_client` should be
`delete_order` — which blocks the whole `app.crud` package from importing normally (every test
above needed a `sys.modules` workaround to bypass it). Tracked under Phase 5
(`05-orders-and-products.md`), but it will block Phase 4's router wiring too if not fixed first.
