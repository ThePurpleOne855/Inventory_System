from typing import Optional
from sqlmodel import Session, select
from app.models.client import Client
from app.schema.client import ClientUpdate
from pydantic import EmailStr


def create_client(session: Session, client_data: Client) -> Client:
    session.add(client_data)
    session.commit()
    session.refresh(client_data)
    return client_data

def get_client_by_email(session: Session, client_email: EmailStr) -> Client | None:
    return session.exec(
        select(Client).where(Client.email == client_email)
    ).first()


def get_client_by_id(session: Session, client_id: int) -> Optional[Client]:
    return session.get(Client, client_id)


def get_clients(session: Session, offset: int = 0, limit: int = 100) -> list[Client]:
    statement = select(Client).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def update_client(session: Session, client_id: int, client_in: ClientUpdate) -> Optional[Client]:
    client_obj = session.get(Client, client_id)
    if not client_obj:
        return None

    update_data = client_in.model_dump(exclude_unset=True) # Only fields sent
    client_obj.sqlmodel_update(update_data)
    session.add(client_obj)
    session.commit()
    session.refresh(client_obj)
    return client_obj


def delete_client(session: Session, client_id: int) -> bool:
    client_obj = session.get(Client, client_id)
    if not client_obj:
        return False

    session.delete(client_obj)
    session.commit()
    return True