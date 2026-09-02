from sqlmodel import Session, select
from app.service.client_exceptions import ClientNotFoundByIdError, ClientNotFoundByEmailError, ClientNotFound, ClientNotFoundForUpdate
from app.models.client import Client
from app.schema.client import ClientSearchParams
from app.crud.client import create_client, get_client_by_email, get_client_by_id, get_clients, update_client, delete_client, search_client
from app.core.security import hash_password
from typing import Optional

from sqlalchemy.exc import NoResultFound
from app.schema.client import ClientCreate, ClientUpdate, ClientRead
from pydantic import EmailStr


def register_client_service(session: Session, client_in: ClientCreate) -> ClientRead:
    if get_client_by_email(session, client_in.email):
        raise ValueError("Email already registered")

    client_data = Client(
        email= client_in.email,
        name = client_in.name,
        last_name = client_in.last_name,
        phone_number= client_in.phone_number, 
        hashed_password= hash_password(client_in.password))

    return create_client(session, client_data)

def retrieve_client_by_id_service(session: Session, client_id: int) -> ClientRead:
    client = get_client_by_id(session, client_id)
    if client is None:
        raise ClientNotFoundByIdError(client_id)
    return client

def retrieve_client_by_email_service(session: Session, client_email: EmailStr):
    client = get_client_by_email(session, client_email)
    if client is None:
        raise ClientNotFoundByEmailError(client_email)
    return client

def search_client_service(session: Session, params: ClientSearchParams) -> list[ClientRead]:
    return search_client(session, params)
    
def update_client_service(session: Session, client_id, client_new_data_in: ClientUpdate) -> ClientRead:
    updated = update_client(session, client_id, client_new_data_in)
    
    if updated is None:
        raise ClientNotFoundForUpdate(client_id, client_new_data_in)
    return updated