from sqlmodel import Field, SQLModel, Relationship
from pydantic import field_validator, EmailStr
from app.models import order
from pydantic_extra_types.phone_numbers import PhoneNumber

class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    last_name: str | None = None
    email: EmailStr = Field(index=True, unique=True)
    phone_number: PhoneNumber = Field(index=True)
    
    orders: list["order.Order"] = Relationship(back_populates="client")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v:str) -> str:
        return v.lower()
