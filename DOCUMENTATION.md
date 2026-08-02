# Technologies

Pydantic


Technology Schema and Layer:

Request comes in (JSON)
   ↓
FastAPI receives it → uses Pydantic to validate shape
   ↓
Validated data → passed to a SQLModel instance
   ↓
SQLModel (via SQLAlchemy) → writes it to Postgres
   ↓
Response → FastAPI uses Pydantic again to shape the outgoing JSON