from sqlmodel import Session, select
from app.service.client_exceptions import ClientNotFoundErrorById, ClientNotFoundByEmailError
from app.models.client import *
from app.crud.client import *
from app.core.security import hash_password
from typing import Optional
from sqlalchemy.exc import NoResultFound
from app.schema.client import ClientCreate, ClientUpdate, ClientRead


def register_client(session: Session, client_in: ClientCreate) -> ClientRead:
    if get_client_by_email(session, client_in.email):
        raise ValueError("Email already registered")

    client_data = ClientCreate(
        email= client_in.email,
        name = client_in.name,
        last_name = client_in.last_name,
        phone_number= client_in.phone_number, 
        hashed_password= hash_password(client_in.password))

    return create_client(session, client_data)

def retrieve_client_by_id(session: Session, client_id: int) -> ClientRead:
    try:
        return get_client_by_id(session, client_id)
    except NoResultFound as e:
        raise ClientNotFoundErrorById(client_id) from e

        

    return get_client_by_id(session, client_id)

def retrieve_client_by_email(session: Session, client_email: EmailStr):
    try:
        return get_client_by_email(session, client_email)
    except NoResultFound as e:
        raise ClientNotFoundByEmailError(client_email) from e


def retriev