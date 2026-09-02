from decimal import Decimal
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Product


class OrderProduct(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)

    quantity: int
    unit_price: Decimal

    order: "Order" = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates="order_items")
