from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from models import Client


class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="client.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total: float

    client: Client | None Relationship(back_populates="Orders")
