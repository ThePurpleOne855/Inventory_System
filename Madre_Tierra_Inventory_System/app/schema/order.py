from sqlmodel import SQLModel, Field
from typing import Optional

class OrderBase(SQLModel):
    client_id: int
    total: float

class OrderCreate(OrderBase):
    pass

class OrderRead(OrderBase):
    id: int
    created_at: str

class OrderUpdate(SQLModel):
    client_id: Optional[int] = None
    total: Optional[float] = None

class OrderDelete(SQLModel):
    id: int

class OrderList(SQLModel):
    orders: list[OrderRead]