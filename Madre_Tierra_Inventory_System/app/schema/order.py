from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel
from pydantic import model_validator

from app.schema.client import ClientBase, ClientNewProfile
from app.schema.order_product import OrderProductCreate


class OrderCreate(SQLModel):
    client_id: int | None = None
    client: ClientBase | None = None
    products: list[OrderProductCreate]

    @model_validator(mode="after")
    def validate_client(self):
        if self.client_id is None and self.client is None:
            raise ValueError("Select a client or enter new client details")
        if self.client is not None and not self.client.name.strip():
            raise ValueError("Client name cannot be blank")
        if self.client_id is None and self.client is not None:
            self.client = ClientNewProfile.model_validate(self.client.model_dump())
        return self


class OrderBase(SQLModel):
    client_id: int
    total: Decimal


class OrderRead(OrderBase):
    id: int
    created_at: datetime
    cancelled_at: datetime | None = None


class OrderUpdate(SQLModel):
    client_id: int | None = None


class OrderDelete(SQLModel):
    id: int


class OrderList(SQLModel):
    orders: list[OrderRead]
