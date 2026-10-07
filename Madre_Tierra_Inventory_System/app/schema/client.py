from pydantic import EmailStr, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlmodel import Field, SQLModel


class ClientBase(SQLModel):
    name: str
    last_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zipcode: str | None = None
    email: EmailStr = Field(index=True)
    phone_number: PhoneNumber = Field(index=True)


class ClientNewProfile(ClientBase):
    address: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    country: str = Field(min_length=1)
    zipcode: str = Field(min_length=1)

    @field_validator("name", "address", "city", "state", "country", "zipcode")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value


class ClientCreate(ClientNewProfile):
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
