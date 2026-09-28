from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.schema.order_product import OrderProductCreate


class OrderCreate(SQLModel):
    client_id: int
    products: list[OrderProductCreate]


class OrderBase(SQLModel):
    client_id: int
    total: Decimal


class OrderRead(OrderBase):
    id: int
    created_at: datetime


class OrderUpdate(SQLModel):
    client_id: int | None = None


class OrderDelete(SQLModel):
    id: int


class OrderList(SQLModel):
    orders: list[OrderRead]
