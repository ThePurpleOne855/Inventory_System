# Madre Tierra Inventory System

A FastAPI + SQLModel inventory and order management backend for Madre Tierra, backed by PostgreSQL.

Designed to manage clients, products, and orders (with order line items), using a service
layer between API routers and database access.

## Status

This project is under active development. The database models, schemas, migrations, and CRUD
modules are present. The service layer covers client and product CRUD, order CRUD, and order line
items. Order services calculate totals from current product prices and deduct or restore inventory
when line items are added or removed.

The client, order, and product routers are still route stubs, so the service operations are not
available through HTTP yet. Authentication and analytics are out of scope for the current
development stage and are not mounted in the API.


## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — web framework
- **[SQLModel](https://sqlmodel.tiangolo.com/)** (SQLAlchemy + Pydantic) — ORM and validation
- **[PostgreSQL](https://www.postgresql.org/)** — database
- **[Alembic](https://alembic.sqlalchemy.org/)** — database migrations
- **[Argon2](https://github.com/hynek/argon2-cffi)** — password hashing
- **[uv](https://docs.astral.sh/uv/)** — dependency management
- Python 3.14

## Project Structure

```
Madre_Tierra_Inventory_System/
├── alembic/                # Migrations
└── app/
    ├── core/                # Cross-cutting utilities (password hashing, etc.)
    ├── crud/                # Database access functions
    ├── models/               # SQLModel table models (Client, Order, OrderProduct, Product)
    ├── routers/               # FastAPI route definitions
    ├── schema/                # Pydantic request/response schemas
    ├── service/                # Business logic layer, called by routers
    ├── test/                    # Tests
    ├── database.py              # Engine/session setup
    └── main.py                    # FastAPI app entrypoint
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

This starts a PostgreSQL 16 container on `localhost:5432`.

### 3. Configure environment variables

Create a `.env` file in the project root with:

```
DATABASE_URL=postgresql://madre_tierra_user:<password>@localhost:5432/madre_tierra_db
```

Use the credentials defined in `docker-compose.yaml` (or your own database).

### 4. Apply migrations

```bash
cd Madre_Tierra_Inventory_System
uv run alembic upgrade head
```

### 5. Run the app

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

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

The client, order, and product route prefixes are registered, but their handlers are currently
stubs. The interactive docs at `/docs` show the declared routes and schemas, not completed
workflows. Authentication and analytics routes are not mounted.

## Running Tests

```bash
uv run pytest app/test/test_relationships.py
```

The relationship test checks the Client ↔ Order model mapping. It passed when last run.

## Notes

- Never commit `.env` — it holds the live database connection string.
