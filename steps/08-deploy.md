# Phase 8 — Get it out of your laptop

**Why deploy near the end, not the middle:** deploying earlier just means re-deploying every
time you fix the next layer's bugs — better to deploy once the API surface (all three resources
+ auth) is stable and tested locally, so the deploy step validates infrastructure, not
application bugs.

**Status as of 2026-08-31: not started.**

## Repo/config hygiene

- [ ] Drop `requirements.txt` — still present, still out of sync with `pyproject.toml` (which is
      the real source of truth per `uv.lock`), or regenerate it with `uv export` only right
      before a deploy that specifically needs it.
- [ ] Move `.env` values to `pydantic-settings`-driven config (today `database.py` reads
      `os.environ["DATABASE_URL"]` directly via `python-dotenv`); add `.env` to `.gitignore` —
      **still not present in `.gitignore`**, still tracked in git — and commit a `.env.example`
      instead. Current `.env` value
      (`postgresql+psycopg2://postgres:root@localhost:5432/postgres`) is a local-only
      docker-compose credential, not yet a real secret, but the pattern is dangerous the moment
      one lands here.
- [ ] Review `.claude/worktrees/bridge-cse_...` — check whether this is still present and
      tracked; unrelated to the app if so.

## Deploy

- [ ] **Database**: swap to a managed Postgres (Neon, Supabase, Railway, or RDS) once
      `database.py` reads `DATABASE_URL` from env.
- [ ] **App hosting**: deploy the FastAPI app (Railway, Fly.io, Render, or a container on
      AWS/GCP) — pick based on desired exposure.

## Done when

The app runs against a managed Postgres instance and is reachable at a public URL, with no
secrets committed to the repo.
