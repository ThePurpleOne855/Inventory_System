# Phase 6 — Lock in correctness with a safety net

**Why here, not earlier or later:** too early and there's nothing working yet to test
meaningfully. Too late (e.g. after auth and deploy) and you'll have shipped more bugs of the
same shape without a net. Right after all three resources work is the point of maximum leverage
— you're about to start touching auth and cross-cutting concerns, exactly when a regression is
easiest to introduce and hardest to notice by eye.

**Status as of 2026-08-31: not started** (the real thing this phase asks for). Note:
`app/test/test_relationships.py` now exists, but it's a narrow unit test for Phase 1's
`Client`↔`Order` mapper fix (`configure_mappers()` + relationship assertions) — not the
`TestClient`-driven full-CRUD smoke suite this phase calls for, and it can't be written for real
until Phase 4/5's routers actually do something.

## Checklist

- [x] A `test/` directory now exists (`app/test/`), though not the `tests/` name/location
      originally suggested — either is fine, just be consistent.
- [ ] Add a one-file smoke test: `from app.main import app`, then a `TestClient` hitting every
      router's full CRUD cycle (create → read → update → delete, plus one not-found case) for
      `clients`, `orders`, and `products`. Blocked until Phases 4 and 5 wire the routers.

This single test file would have caught nearly every bug catalogued in `improvement.md`: broken
imports, a wrong schema type, an unregistered route, a truncated function — immediately instead
of on the next manual audit.

## Done when

`pytest` runs the smoke test suite green against a real (or test) database, covering all three
resources' full CRUD cycles.
