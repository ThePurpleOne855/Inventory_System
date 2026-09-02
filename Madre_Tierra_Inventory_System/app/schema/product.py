from decimal import Decimal

from sqlmodel import SQLModel


class ProductBase(SQLModel):
    name: str
    description: str | None = None
    price: Decimal
    quantity: int


class ProductCreate(ProductBase):
    quantity: int = 0


class ProductRead(ProductBase):
    id: int


class ProductUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    quantity: int | None = None


class ProductDelete(SQLModel):
    id: int
