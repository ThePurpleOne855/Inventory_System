from typing import Literal

from pydantic import Field
from sqlmodel import SQLModel


class BroadcastRequest(SQLModel):
    """A message to send to many clients, one email each."""

    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    # Empty or omitted means "every client".
    client_ids: list[int] | None = None


class RecipientResult(SQLModel):
    client_id: int
    name: str
    email: str
    status: Literal["sent", "failed"]
    detail: str = ""


class BroadcastResult(SQLModel):
    sent: int
    failed: int
    results: list[RecipientResult]


class MailStatus(SQLModel):
    """Whether the server can send mail at all, so the UI can say so up front."""

    configured: bool
    host: str = ""
    sender: str = ""
