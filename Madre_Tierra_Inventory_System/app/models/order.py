from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.order_product import OrderProduct


def utc_now() -> datetime:
    # Stored as naive UTC; the dashboard converts to the business time zone.
    return datetime.now(UTC).replace(tzinfo=None)


class Order(SQLModel, table=True):
    __tablename__ = "orders"  # pyright: ignore[reportAssignmentType]
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id", index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    cancelled_at: datetime | None = None
    total: Decimal = Field(max_digits=10, decimal_places=2)

    client: Optional["Client"] = Relationship(back_populates="orders")  # noqa
    items: list["OrderProduct"] = Relationship(back_populates="order")
