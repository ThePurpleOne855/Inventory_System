from sqlmodel import SQLModel, Field
from pydantic import EmailStr, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing import Optional

class ClientBase(SQLModel):
    name: str
    last_name: Optional[str] = None
    email: EmailStr = Field(index=True)
    phone_number: PhoneNumber = Field(index=True)

class ClientCreate(ClientBase):

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v
    password: str

class ClientRead(ClientBase):
    id: int    

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[PhoneNumber] = None


class ClientLogin(SQLModel):
    email: str
    password: str

class ClientDelete(SQLModel):
    id: int