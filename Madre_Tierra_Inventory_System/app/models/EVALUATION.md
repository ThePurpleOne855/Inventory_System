# Models Evaluation — Madre Tierra Inventory System

Reviewed: `app/models/client.py`, `app/models/order.py`, `app/models/product.py`, `app/models/__init__.py`
Verified by actually importing each module with the project's `.venv` (not just reading).

## Critical (breaks the app)

### 1. `order.py:12` — syntax error, missing `=`
```python
client: Client | None Relationship(back_populates="Orders")
```
There is no `=` before `Relationship(...)`. This is not valid Python — the module fails to
parse and raises `SyntaxError` on import. Confirmed by running `import models.order`:
```
SyntaxError: invalid syntax
client: Client | None Relationship(back_populates="Orders")
                       ^^^^^^^^^^^^
```
Fix:
```python
client: Client | None = Relationship(back_populates="orders")
```

### 2. `back_populates` mismatch between `Client` and `Order`
- `client.py:11` → `orders: list["Order"] = Relationship(back_populates="client")`
- `order.py:12` → `Relationship(back_populates="Orders")` (capital "O")

`back_populates` must exactly match the **attribute name** on the other model. The attribute
on `Client` is `orders` (lowercase), so `"Orders"` will raise a SQLAlchemy mapper
configuration error (`Mapper has no property 'Orders'`) once the syntax error above is fixed.
Both sides need to agree: `client` ↔ `orders`.

### 3. `order.py:3` — `from models import Client` will fail
`app/models/__init__.py` is empty, so it does not re-export `Client`. Verified directly:
```
>>> from models import Client
ImportError: cannot import name 'Client' from 'models'
```
Either populate `__init__.py` with `from .client import Client`, or import directly:
```python
from models.client import Client
```
Also worth watching: importing `Client` directly (not as a string) in `order.py` while
`client.py` only references `"Order"` as a forward-ref string sets up a one-directional
import. If `Client` ever needs a real (non-string) reference back, this becomes a circular
import; keeping both sides as string forward refs (SQLModel supports this) is safer.

## Bugs / modeling issues

### 4. `order.py:8` — field named `user_id` but points at `client`
```python
user_id: int = Field(foreign_key="client.id", index=True)
```
There is no `User` model anywhere in this codebase — the relationship is to `Client`. This
should be `client_id` for clarity and to match the FK target and the `client` relationship
attribute below it.

### 5. `product.py` is empty
No `Product` model exists. `Order` currently only has a `total: float` with no line items —
there's no way to know *what* was ordered, just an amount. If the intent is a real
inventory/order system, you likely need a `Product` model and an `OrderItem`/`OrderLine`
join model (order ↔ product, quantity, unit price), rather than a bare `total` on `Order`.

### 6. `"order"` as a table name is a reserved SQL keyword
SQLModel will default the table name to `order` (lowercase class name). `ORDER` is a
reserved word in SQL (as in `ORDER BY`) and can cause quoting issues with some databases/raw
SQL/migration tools. Consider an explicit `__tablename__ = "orders"`.

### 7. `datetime.utcnow()` is deprecated
`order.py:9` — `default_factory=datetime.utcnow`. Deprecated since Python 3.12 in favor of
timezone-aware datetimes:
```python
default_factory=lambda: datetime.now(timezone.utc)
```

## Minor / cleanup

### 8. `client.py:1` — unused import
`create_engine` is imported but never used in `client.py`. Engine creation belongs in a
database/session setup module (`app/crud/database.py`), not the model file — and that file
is currently empty, so there's no engine/session wiring anywhere in the project yet.

### 9. `app/crud/main.py` and `app/crud/database.py` are both empty
No DB engine, session factory, or CRUD functions exist yet, so nothing in `models/` can
actually be persisted or queried at this point.

## What already looks fine
- `Client` model (`client.py`) imports and builds its table correctly on its own —
  verified `SQLModel.metadata.create_all()` succeeds for `Client` in isolation.
- `EmailStr` normalization via `field_validator` is a nice touch (lowercases email on
  validation).
- Using `EmailStr` and `PhoneNumber` (via `pydantic-extra-types`) for validated columns is a
  good practice, and both map to plain string columns correctly under SQLModel.

## Priority to fix
1. Fix the `order.py` syntax error (blocks everything).
2. Fix `back_populates` mismatch (`"Orders"` → `"orders"`).
3. Fix the `Client` import in `order.py` (either export it from `__init__.py` or import
   directly from `models.client`).
4. Decide on `Product`/order-line modeling before building CRUD on top of `Order`.
