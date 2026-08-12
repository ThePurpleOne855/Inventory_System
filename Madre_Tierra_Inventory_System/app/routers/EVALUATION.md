# Routers Evaluation — Madre Tierra Inventory System

Reviewed: `app/routers/clients.py`, `app/routers/orders.py`, `app/routers/products.py`,
`app/routers/auth.py`, `app/routers/analytics.py`, plus `app/main.py` and `app/__init__.py`
since they determine whether any router can actually be reached.
Verified by actually importing/compiling the modules with the project's `.venv`, not just reading.

## Critical — the app cannot run at all right now

### 1. `app/__init__.py` contains a stray `s`
The entire file is one line: `s`. That's a bare name reference with no assignment — importing
the `app` package raises immediately:
```
NameError: name 's' is not defined
```
Since every router lives under `app.*`, this blocks importing *anything* — routers, models,
main.py — the moment someone does `import app` or `uvicorn app.main:app`. This is the single
highest-priority fix in the whole project; nothing else here matters until it's empty (or
removed entirely).

### 2. `app/main.py` is empty
There is no `FastAPI()` instance anywhere in `main.py`, and no `include_router(...)` calls. None
of the four routers (`clients`, `orders`, `products`, `analytics`/`auth` once they exist) are
wired into an app. Right now there is nothing for `uvicorn` to serve.

### 3. `clients.py` instantiates its own `FastAPI()` app
```python
from fastapi import FastAPI, APIRouter
app = FastAPI()
```
A router module should only build an `APIRouter`; the `FastAPI()` instance belongs in
`main.py`. This looks like a copy-paste leftover — it's dead code that will confuse whoever
reads this file next (there are now two "apps" in the codebase, and only one is wrong-but-real).
Delete the `FastAPI` import and the `app = FastAPI()` line.

### 4. `products.py` — missing `@` decorator, so `GET /products/` doesn't exist
```python
router.get("/")
def list_products():
    pass
```
`router.get("/")` returns a decorator and the return value is discarded — without the `@`,
`list_products` is never registered. Calling `GET /products/` will 404 (route not found), not
just return an empty/unimplemented response. Easy to miss on a skim; only shows up if you
actually hit the endpoint or print `router.routes`.

## Bugs — routes exist but can't do what they claim

### 5. `products.py` and `orders.py` create/update endpoints have no request body parameter
```python
# products.py
def create_product():          # no `product: ProductCreate` param
def update_product(product_id: int):   # no `product: ProductUpdate` param

# orders.py
def create_order():            # no `order: OrderCreate` param
def update_order(order_id: int):       # no `order: OrderUpdate` param
```
Neither `orders.py` nor `products.py` even imports its schema module. As written, a client has
no way to send data to these endpoints — compare with `clients.py`, which does declare
`client: ClientCreate` / `client: ClientUpdate` correctly. Fix by importing the schemas and
adding the body parameter, mirroring `clients.py`.

### 6. No endpoint anywhere is implemented — all bodies are `pass`
Every path operation across all three resource routers is a stub. None of them call into
`app/crud/*.py` (which are themselves empty files) or take a `Session` dependency — there is no
`get_session`/`Depends(...)` pattern anywhere in the codebase yet, and no `database.py` to
provide one. This is expected at this stage, but it's worth being explicit that **the routers
currently define shape, not behavior** — see "Suggested next steps" below for build order.

### 7. No `response_model` on any endpoint
None of `list_clients`, `get_client`, `create_client`, etc. declare `response_model=`. FastAPI
can't validate or document the output shape, and `/docs` will show no useful response schema.
Once CRUD is wired, pair each endpoint with its `Read` schema, e.g.:
```python
@router.get("/", response_model=list[ClientRead])
@router.get("/{client_id}", response_model=ClientRead)
@router.post("/", response_model=ClientRead, status_code=201, ...)
```

## Inconsistencies between the three resource routers

### 8. `products.py` has no `DELETE /{product_id}`
`clients.py` and `orders.py` both have a delete endpoint; `products.py` stops at `PUT`. Decide
if that's intentional (e.g. products are "deactivated" not deleted) or just an oversight — if
inventory items should never hard-delete, make that explicit with a comment or a `soft_delete`
field instead of silently omitting the route.

### 9. `orders.py`'s create endpoint has no `status_code=201`
`clients.py` and `products.py` both set `status_code=201` (and document a `409` response) on
their POST endpoints; `orders.py`'s `create_order()` uses FastAPI's default `200`. Pick one
convention (201 for all resource creation is the more correct REST default) and apply it
everywhere.

### 10. No 404 handling pattern established anywhere
Once `get_client`/`get_order`/`get_product` actually query the DB, a not-found case needs
`raise HTTPException(status_code=404, detail=...)`. Worth deciding this pattern once (maybe a
small `crud` helper like `get_or_404`) rather than each router improvising its own.

## Missing pieces that block wiring routers to real data

### 11. `crud/client.py`, `crud/order.py`, `crud/product.py` are all empty
Routers have nothing to call. This is the next real layer of work — see build order below.

### 12. No DB session dependency exists anywhere
No `database.py`, no `engine`, no `get_session()` generator, no `Depends(get_session)` used in
any router signature. This has to exist before any router body can do more than `pass`.

### 13. `auth.py` and `analytics.py` are both completely empty (0 bytes)
Not even an `APIRouter()` instance. `schema/client.py` already defines `ClientLogin`
(email + password), so there's clearly an intent to have a login endpoint, but there's nowhere
for it to live yet, and no password-hashing utility anywhere in `crud/`. `analytics.py` matches
the AI/SQL-analysis feature described in the root `improvement.md` — correctly left for last.

### 14. `models/order.py`'s `__tablename__="orders"` kwarg is silently ignored
Not a router bug directly, but it will bite the first router that queries orders: verified by
actually importing the model — `Order.__table__` prints `order`, not `orders`, despite the
class being written as `class Order(SQLModel, table=True, __tablename__="orders"):`. SQLModel
doesn't support `__tablename__` as a class keyword argument; it has to be a normal class-body
assignment:
```python
class Order(SQLModel, table=True):
    __tablename__ = "orders"
```
`order` is a reserved SQL word (`ORDER BY`), so this is worth fixing before any router runs raw
or generated SQL against it (relevant for the planned analytics/AI feature too).

### 15. `OrderBase.user_id` naming vs. the `Client` model
`schema/order.py`'s `OrderBase.user_id` and `models/order.py`'s `Order.user_id` both use
`user_id`, but there is no `User` model anywhere — the foreign key targets `Client`. Once
`orders.py`'s create/update endpoints get real body params (finding #5), they'll inherit
whatever field name the schema uses. Rename to `client_id` in both the model and schema before
wiring CRUD, so the router's request body reads correctly (`{"client_id": 1, "total": 42.0}`).

## What already looks fine
- `APIRouter(prefix=..., tags=...)` is used consistently across all three resource routers —
  good, keep this pattern for `auth.py` and `analytics.py` too.
- `clients.py` correctly imports and type-hints its schemas (`ClientCreate`, `ClientUpdate`) on
  the endpoints that need a body — this is the pattern `orders.py`/`products.py` should copy.
- The `responses={409: {...}}` documentation on `create_client`/`create_product` is a nice
  touch for `/docs` — worth extending to `create_order` too once relevant (duplicate orders
  probably isn't a real conflict case, but worth a deliberate decision either way).

## Suggested next steps (priority order)

1. **Unblock imports.** Empty `app/__init__.py`. This alone is why nothing below can be tested
   end-to-end yet.
2. **Remove the stray `FastAPI()` from `clients.py`.**
3. **Fix `products.py`'s missing `@` decorator** on `list_products`.
4. **Add the missing body parameters** to `create_product`, `update_product`, `create_order`,
   `update_order` (finding #5) — import the schemas while you're there.
5. **Build the session dependency** (`app/database.py` or `app/core/database.py`: engine +
   `get_session()`), since every router body needs it next.
6. **Implement `crud/client.py` first** (it's the most complete model) and wire `clients.py`'s
   five endpoints to it end-to-end, including `response_model=` and 404 handling. Get this one
   resource fully working and tested in `/docs` before copying the pattern to
   products/orders — easier to debug one working example than three half-wired ones at once.
7. **Fix `Order.user_id` → `client_id` and the `__tablename__` bug** before wiring `orders.py`
   to CRUD, so you're not building on a field name / table name you'll have to rename later.
8. **Wire `app/main.py`**: create the `FastAPI()` instance, `include_router()` for each
   resource, confirm `/docs` shows all routes.
9. **`auth.py` last of the CRUD routers** — needs password hashing in `crud/client.py`
   (`ClientCreate.password` currently has nowhere to go) before a login endpoint means anything.
10. **`analytics.py`** stays last, per the root `improvement.md` — it depends on stable schemas
    and real data to describe to the model, and carries its own SQL-safety guardrails to design
    (see root `improvement.md`, Decision 5).
