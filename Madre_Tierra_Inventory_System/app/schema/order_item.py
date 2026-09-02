from decimal import Decimal

from sqlmodel import SQLModel


class OrderProductBase(SQLModel):
    product_id: int
    quantity: int


class OrderProductCreate(OrderProductBase):
    pass


class OrderProductRead(OrderProductBase):
    id: int
    order_id: int
    unit_price: Decimal


class OrderProductUpdate(SQLModel):
    quantity: int | None = None


class OrderProductDelete(SQLModel):
    id: int
