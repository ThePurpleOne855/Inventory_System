from pydantic import EmailStr, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlmodel import Field, SQLModel


class ClientBase(SQLModel):
    name: str
    last_name: str | None = None
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
    name: str | None = None
    email: EmailStr | None = None
    phone_number: PhoneNumber | None = None


class ClientSearchParams(ClientBase):
    name: str | None = None
    email: EmailStr | None = None
    phone_number: PhoneNumber | None = None


class ClientLogin(SQLModel):
    email: str
    password: str


class ClientDelete(SQLModel):
    id: int
