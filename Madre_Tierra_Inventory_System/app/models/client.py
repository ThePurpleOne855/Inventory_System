from typing import TYPE_CHECKING

from pydantic import EmailStr, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.order import Order


class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    last_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zipcode: str | None = None
    email: EmailStr = Field(index=True, unique=True)
    phone_number: PhoneNumber = Field(index=True)
    source: str | None = Field(default=None, max_length=50)
    hashed_password: str

    orders: list["Order"] = Relationship(back_populates="client")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()
