# Next Steps

Working checklist form of `../improvement.md`'s "Guided build order." Each file is one phase:
a goal, a checklist, and a "done when" line so you know when to move to the next file. The
*why* behind each phase (and full bug-level detail) lives in `improvement.md` — these files are
the short version to work from day to day; go back to `improvement.md` when you want the
reasoning or a second opinion.

Work through them in order — each phase is sequenced so you can actually verify the previous one
before starting the next, not by importance.

**Status snapshot (2026-08-31)** — see each file for the item-by-item detail:

1. [Make the app importable](01-make-app-importable.md) — ✅ done, verified by test
2. [Give the app somewhere to persist data](02-persist-data.md) — ✅ done, migration applied and verified against a live DB
3. [Fix the client service layer](03-fix-client-service.md) — ✅ done, verified against a live DB (a Phase 5 `crud/__init__.py` bug will block Phase 4 if not fixed first — see note in the file)
4. [Prove `clients` works end-to-end](04-clients-end-to-end.md) — ❌ not started (routers still `pass`)
5. [Repeat the pattern for orders and products](05-orders-and-products.md) — ❌ not started
6. [Add a smoke-test safety net](06-smoke-tests.md) — ❌ not started (a narrow Phase-1 unit test exists, not the CRUD suite)
7. [Filtering and auth](07-filtering-and-auth.md) — ❌ not started
8. [Deploy](08-deploy.md) — ❌ not started
9. [AI-powered SQL analytics](09-ai-sql-analytics.md) — ❌ not started

When a phase's checklist changes state (done, blocked, bug found), update that file — and if the
underlying analysis changes, update `improvement.md` too, since these files summarize it rather
than replace it.
