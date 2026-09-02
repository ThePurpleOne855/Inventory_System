# Phase 9 — The one deliberately-last feature: AI-powered SQL analytics

**Why last, on purpose:** this is the highest-risk feature in the project — letting a model
generate SQL that runs against your database is one hallucination or prompt injection away from
a destructive query. It also needs a stable, finished schema to describe to the model, and real
data to be useful to test against. Building it earlier means building it twice.

**The core risk:** treat model output like untrusted user input.

**Status as of 2026-08-31: not started.** `routers/analytics.py` is still 0 bytes, correctly left
for last.

## Checklist

- [ ] **Read-only DB role** — a Postgres role (`GRANT SELECT ONLY`) used exclusively by this
      feature. Never let generated SQL run under a role that can write.
- [ ] **Schema-scoped prompting** — give the model your actual table/column definitions, not the
      whole DB, in the system prompt.
- [ ] **Validate before executing** — parse the generated SQL (e.g. `sqlglot`) and assert it's a
      single `SELECT` touching only allow-listed tables before running it. Reject anything else.
- [ ] **Row/result limits** — inject a `LIMIT` if the model didn't include one; cap execution
      time (`statement_timeout`).
- [ ] **Show the user the generated SQL**, not just the answer — trust feature and debugging aid.

## Suggested flow

`POST /analytics/ask` → build prompt with schema + question → call LLM → validate SQL → execute
against the read-only connection → return `{sql, columns, rows}`.

## Done when

A question against `/analytics/ask` returns real data via a validated, read-only, row-limited
query, with the generated SQL visible in the response.
