# Phase 7 — Round out what a real API needs

**Why auth this late, not earlier:** it was genuinely blocked until now — it needs a working
`hashed_password` column (Phase 2) and a bug-free `client_service` (Phase 3) to check
credentials against. Doing it earlier would mean building auth against a service layer known to
be broken.

**Status as of 2026-08-31: not started.** `routers/auth.py` is still 0 bytes.

## Checklist

- [ ] Filtering params on list endpoints for `orders`/`products`, matching the pattern already
      started for `clients` via `ClientSearchParams` (a `FilterParams` dependency per resource
      built with SQLModel's `select()` + conditional `.where()` clauses). Note: `ClientSearchParams`
      itself still needs the `phone_number`-optional fix from Phase 3 before it's a solid pattern
      to copy.
- [ ] `app/routers/auth.py` (still 0 bytes): a login endpoint calling
      `retrieve_client_by_email_service` + `verify_password`.
- [ ] A dependency other routers can use to require authentication.

## Done when

List endpoints support filtering, and a login endpoint issues something (session/token) that a
dependency can validate to gate other routes.
