from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.order_product import OrderProduct


class Order(SQLModel, table=True):
    __tablename__ = "orders"  # pyright: ignore[reportAssignmentType]
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total: float

    client: Optional["Client"] = Relationship(back_populates="orders")  # noqa
    items: list["OrderProduct"] = Relationship(back_populates="order")
