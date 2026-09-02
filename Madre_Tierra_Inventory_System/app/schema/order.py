from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel


class OrderBase(SQLModel):
    client_id: int
    total: Decimal


class OrderCreate(OrderBase):
    pass


class OrderRead(OrderBase):
    id: int
    created_at: datetime


class OrderUpdate(SQLModel):
    client_id: int | None = None
    total: Decimal | None = None


class OrderDelete(SQLModel):
    id: int


class OrderList(SQLModel):
    orders: list[OrderRead]
