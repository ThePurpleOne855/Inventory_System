# Phase 5 — Repeat the proven pattern for `orders` and `products`

**Why not all three in parallel from the start:** by this point the pattern is proven; the
remaining work is repetition of Phases 3+4 plus fixing the specific bugs below — low-risk,
high-speed work rather than design work.

**Status as of 2026-08-31: not started.** Every bug below still reproduces exactly as originally
found; `order_service.py` and `product_service.py` are still empty files (0 bytes).

## Router bugs to fix while wiring

- [ ] `orders.py`: `create_order()` takes no body parameter and doesn't import `OrderCreate` —
      there's currently no way to send it data.
- [ ] `orders.py`: `update_order(order_id: int, client: ClientUpdate)` is typed with
      `ClientUpdate` instead of `OrderUpdate` — looks like an uncorrected copy-paste from
      `clients.py`.
- [ ] `products.py`: no `DELETE /{product_id}` yet (inconsistent with the other two resources —
      decide deliberately whether products should hard-delete at all).
- [ ] `products.py`: `create_product`/`update_product` take no body parameter and don't import
      `ProductCreate`/`ProductUpdate`.

## Schema bug to fix along the way

- [ ] `schema/order.py`: `OrderRead.created_at: str` but the model field is `datetime`. Pydantic
      v2 doesn't coerce `datetime` → `str` for a plain `str` field — this raises a response
      validation error the first time an order is returned. Change to `datetime`.

## Checklist

- [ ] Build out `order_service.py` and `product_service.py` following the same shape as the
      now-fixed `client_service.py`.
- [ ] Wire `orders.py`/`products.py` the same way `clients.py` was wired in Phase 4.
- [ ] Extend `include_router()` in `main.py` to cover `orders` and `products`.

## Done when

All three resources support create/read/update/delete (and search where applicable) through
`/docs` against the real database.
