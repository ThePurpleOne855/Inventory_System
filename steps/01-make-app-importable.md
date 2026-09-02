# Phase 1 — Make the app importable at all

**Why first:** every later phase involves running code to check it works. Until imports succeed
and the ORM mappers can be configured, "does this work" isn't answerable.

## Checklist

- [x] Empty `Madre_Tierra_Inventory_System/app/__init__.py` — confirmed empty now (the stray `s`
      is gone).
- [x] Fix the `Client` ↔ `Order` relationship in `app/models/`. Done differently than originally
      suggested below, but it works: both `client.py` and `order.py` import each other only
      under `if TYPE_CHECKING:` and use quoted forward references (`"Order"`, `"Client"`) in the
      `Relationship(...)` annotations, so there's no runtime cross-import at all. Verified by
      `app/test/test_relationships.py`, which calls `sqlalchemy.orm.configure_mappers()` and
      asserts both relationship names — `uv run pytest app/test/test_relationships.py` passes.

  Original suggested fix (kept for reference — not what was actually implemented):

  ```python
  # models/order.py
  from app.models.client import Client

  class Order(SQLModel, table=True):
      __tablename__ = "orders"
      client: Optional["Client"] = Relationship(back_populates="orders")
  ```

  ```python
  # models/client.py — no import of order.py
  class Client(SQLModel, table=True):
      orders: list["Order"] = Relationship(back_populates="client")
  ```

## Done when

`import app` succeeds and `sqlalchemy.orm.configure_mappers()` runs without raising. ✅ Verified
2026-08-31 via `app/test/test_relationships.py`.
