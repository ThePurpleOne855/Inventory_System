from sqlmodel import Field, SQLModel, create_engine, Relationship
from pydantic import field_validator, EmailStr
from pydantic_extra_types.phone_numbers import PhoneNumber

class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: EmailStr = Field(index=True, unique=True)
    phone_number: PhoneNumber = Field(index=True)
    
    orders: list["Order"] = Relationship(back_populates="client")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v:str) -> str:
        return v.lower()
