from datetime import datetime

from sqlmodel import Field, SQLModel


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_session"

    token_hash: str = Field(primary_key=True, max_length=64)
    credentials_fingerprint: str = Field(max_length=64)
    expires_at: datetime = Field(index=True)
