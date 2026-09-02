from typing import Optional
from sqlmodel import Session, select
from app.models.client import Client
from app.schema.client import ClientUpdate, ClientSearchParams
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError


def create_client(session: Session, client_data: Client) -> Client:
    session.add(client_data)
    session.commit()
    session.refresh(client_data)
    return client_data

def get_client_by_email(session: Session, client_email: EmailStr) -> Optional[Client]:
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
    
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("Email already registered to another client")
    session.refresh(client_obj)
    return client_obj


def delete_client(session: Session, client_id: int) -> bool:
    client_obj = session.get(Client, client_id)
    if not client_obj:
        return False

    session.delete(client_obj)
    session.commit()
    return True

def search_client(session: Session, params: ClientSearchParams, limit: int = 50, offset: int = 0):
    query = select(Client)

    if params.name is not None:
        query = query.where(Client.name.ilike(f"%{params.name}%"))

    if params.last_name is not None:
        query = query.where(Client.last_name.ilike(f"%{params.last_name}%"))

    if params.email is not None:
            query = query.where(Client.email.ilike(f"%{params.email}%"))

    if params.phone_number is not None:
            query = query.where(Client.phone_number.ilike(f"%{params.phone_number}%"))

    query = query.offset(offset).limit(limit)

    return session.exec(query).all()
    