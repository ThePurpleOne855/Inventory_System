# Madre Tierra Inventory System

A FastAPI + SQLModel inventory and order management backend for Madre Tierra, backed by PostgreSQL.

Designed to manage clients, products, and orders (with order line items), using a service
layer between API routers and database access.

## Status

This project is under active development. The database models, schemas, migrations, and CRUD
modules are present. The service layer covers client and product CRUD, order CRUD, and order line
items. Order services calculate totals from current product prices and deduct or restore inventory
when line items are added or removed.

The client, order, and product routers expose these services through HTTP, including client
search and order line-item operations. All inventory routes require authentication as the
single configured operator. Analytics is not mounted in the API.

Invoices are generated server-side as PDFs and can be emailed to the client as an attachment.
Broadcast email to clients is supported over SMTP. A React front end in `frontend/` covers
clients, product inventory, orders, invoicing, and messaging.


## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — web framework
- **[SQLModel](https://sqlmodel.tiangolo.com/)** (SQLAlchemy + Pydantic) — ORM and validation
- **[PostgreSQL](https://www.postgresql.org/)** — database
- **[Alembic](https://alembic.sqlalchemy.org/)** — database migrations
- **[Argon2](https://github.com/hynek/argon2-cffi)** — password hashing
- **[uv](https://docs.astral.sh/uv/)** — dependency management
- **[ReportLab](https://www.reportlab.com/opensource/)** — invoice PDF generation
- Python 3.14

Front end (`frontend/`): **React 19**, **TypeScript**, **Vite**, **Tailwind CSS**,
**React Router**. See [`frontend/README.md`](frontend/README.md).

## Project Structure

```
├── frontend/               # React + Vite admin UI (see frontend/README.md)
└── Madre_Tierra_Inventory_System/
    ├── alembic/            # Migrations
    └── app/
        ├── core/        # Operator auth, password hashing, settings
        ├── crud/        # Database access functions
        ├── models/      # SQLModel tables (Client, Order, OrderProduct, Product, AuthSession)
        ├── routers/     # FastAPI route definitions
        ├── schema/      # Pydantic request/response schemas
        ├── service/     # Business logic, called by routers
        ├── test/        # Tests
        ├── database.py  # Engine/session setup
        └── main.py      # FastAPI app entrypoint
```

## Getting Started

### Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Docker (for the PostgreSQL database) or a local PostgreSQL instance

### 1. Install dependencies

```bash
uv sync
```

### 2. Start the database

```bash
docker compose up -d
```

This starts a PostgreSQL 16 container on `127.0.0.1:5433`.

### 3. Configure environment variables

Create a `.env` file in the project root with:

```
DATABASE_URL=postgresql://madre_tierra_user:<password>@127.0.0.1:5433/madre_tierra_db
```

Use the credentials defined in `docker-compose.yaml` (or your own database).

### 4. Apply migrations

```bash
cd Madre_Tierra_Inventory_System
uv run alembic upgrade head
```

### 5. Configure the operator

From `Madre_Tierra_Inventory_System/`, run:

```bash
uv run python -m app.core.setup_auth
```

Enter a username and a password of at least 12 characters. The command saves the
username and an Argon2 password hash in the project root's ignored `.env.auth` file,
with permissions restricted to the file owner. It does not store the plaintext password.
For deployments, you can instead supply `AUTH_USERNAME` and `AUTH_PASSWORD_HASH`
as environment variables; environment variables take precedence over the file.

### 6. Run the app

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

### 7. Run the front end

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The UI is served at `http://localhost:5173` and proxies `/api/*` to the API on port
8000, so no CORS configuration is needed in development. Sign in with the operator
credentials from step 5. See [`frontend/README.md`](frontend/README.md) for details.

### 8. Optional: invoicing and email settings

Copy the keys you need from [`.env.example`](.env.example) into `.env`: company
details printed on invoices, and SMTP credentials for emailing invoices and client
broadcasts. Both are optional — the API runs without them, and the Messages page
reports that sending is disabled until SMTP is set.

## Authentication

One operator has access to all inventory operations. Customer `Client` records are
business data and do not grant operator access. There is no public account registration.

1. Call `POST /auth/login` with a JSON body containing `username` and `password`.
   The response contains `access_token`, `token_type: "bearer"`, and `expires_in: 28800`.
2. Send `Authorization: Bearer <access_token>` on inventory requests. In `/docs`,
   use **Authorize** and paste the token returned by login.
3. Use `GET /auth/me` to retrieve the current operator username, and
   `POST /auth/logout` to revoke the current session (HTTP 204).

Sessions expire after eight hours and are stored in the database as SHA-256 token
hashes. Logout revokes the token immediately; sessions survive server restarts.
Expired sessions are removed on subsequent successful logins. Use HTTPS when
accessing the API outside local development, and keep bearer tokens out of URLs and logs.
This session design follows [OWASP session management guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

Login allows five attempts per minute per server process, returning 429 with a
`Retry-After` header when exceeded. This limit is intended for the current single
operator deployment with one server worker; multiple workers need a shared limiter.
Missing or invalid operator configuration returns 503; invalid, revoked, or expired
credentials return 401. `/docs` and `/openapi.json` remain public API documentation.

To change the operator credentials, run `uv run python -m app.core.setup_auth --replace`
from `Madre_Tierra_Inventory_System/`, then restart the API. Existing sessions become
invalid when the new credentials load. If deployment environment variables provide
credentials, update those variables instead. Apply `uv run alembic upgrade head`
before running the authenticated API to create the `auth_session` table.

## Data Model

- **Client** — customer with contact info and a hashed password
- **Product** — inventory item with price and quantity on hand
- **Order** — belongs to a `Client`, has a total and a creation timestamp
- **OrderProduct** — line item joining an `Order` and a `Product`, with quantity and unit price

## API

Routers are mounted with the following prefixes:

- `/clients`
- `/orders`
- `/products`
- `/invoices`
- `/messages`

Each resource supports `GET /` (list), `GET /{id}`, `POST /`, `PUT /{id}`,
and `DELETE /{id}` under its prefix. List endpoints accept `offset` (default 0)
and `limit` (default 100, maximum 100). Updates apply only the supplied fields.
Creates return HTTP 201; deletes return HTTP 200 with `{"id": <deleted ID>}`.

Additional endpoints:

- `GET /clients/search` — filter by name, last name, email, or phone number;
  accepts `offset` and `limit` (default 50).
- `GET /clients/by-email?email=...` — retrieve one client by email.
- `GET /orders/{order_id}/items` — list an order's line items.
- `POST /orders/{order_id}/items` — add a product and quantity, deduct stock,
  and update the order total. Adding an existing product increases its quantity.
- `DELETE /orders/{order_id}/items/{item_id}` — remove a line item belonging
  to this order, restore stock, and update the total.

Order creation accepts `client_id` and a nonempty `products` list containing
`product_id` and `quantity`. Prices and totals are calculated by the service.
Deleting an order restores its inventory. Client responses exclude password fields.

### Invoices

- `GET /invoices/{order_id}` — invoice data for an order: client, line items with
  product names, subtotal, and total, plus the company details from the environment.
- `GET /invoices/{order_id}/pdf` — the same invoice rendered as a one-page A4 PDF,
  returned as an attachment named `INV-00001.pdf`.
- `POST /invoices/{order_id}/email` — email that PDF to the order's client.

Line items keep the `unit_price` recorded when the order was placed, so a later price
change or product deletion never rewrites an existing invoice.

### Messages

- `GET /messages/status` — whether SMTP is configured, so the UI can say so before sending.
- `POST /messages/broadcast` — send one email per client. Takes `subject`, `body`, and
  `client_ids` (`null` or omitted means every client). Each recipient gets their own
  message, so nobody sees the other addresses. The placeholders `{name}`, `{last_name}`,
  and `{full_name}` are filled in per client. The response reports per-recipient
  `sent`/`failed` status rather than failing the whole batch on one bad address.

Email requires `SMTP_HOST` and a sender in the environment — see `.env.example`.
Unconfigured or unreachable mail servers return 503.

Missing records return 404. Duplicate client emails, insufficient stock, and deletion
of clients/products still referenced by orders return 409. Invalid input returns 422.
Interactive request and response schemas are available at `/docs`.

## Running Tests

```bash
PYTHONPATH=Madre_Tierra_Inventory_System uv run pytest Madre_Tierra_Inventory_System/app/test -q
```

Run this command from the project root after `uv sync` (which includes the `httpx`
development dependency). Tests cover model relationships and HTTP CRUD, validation,
conflicts, inventory workflows, login/logout, expiration, credential rotation, and
access control using an isolated SQLite database. They do not
connect to the configured PostgreSQL database.

## Notes

- Never commit `.env` — it holds the live database connection string.
