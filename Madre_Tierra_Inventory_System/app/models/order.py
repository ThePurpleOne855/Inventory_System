from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from app.models import client


class Order(SQLModel, table=True):
    __tablename__="orders"
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total: float

    client: client.Client | None = Relationship(back_populates="orders")
