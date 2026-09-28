from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.security import hash_password
from app.crud.client import (
    create_client,
    delete_client,
    get_client_by_email,
    get_client_by_id,
    get_clients,
    search_client,
    update_client,
)
from app.models.client import Client
from app.schema.client import ClientCreate, ClientSearchParams, ClientUpdate
from app.service.client_exceptions import (
    ClientHasOrdersError,
    ClientNotFoundByEmailError,
    ClientNotFoundByIdError,
    ClientNotFoundForUpdate,
)


def register_client_service(session: Session, client_in: ClientCreate) -> Client:
    if get_client_by_email(session, client_in.email) is not None:
        raise ValueError("Email already registered")

    client = Client(
        email=client_in.email,
        name=client_in.name,
        last_name=client_in.last_name,
        phone_number=client_in.phone_number,
        hashed_password=hash_password(client_in.password),
    )

    try:
        return create_client(session, client)
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("Email already registered") from exc


def retrieve_client_by_id_service(session: Session, client_id: int) -> Client:
    client = get_client_by_id(session, client_id)
    if client is None:
        raise ClientNotFoundByIdError(client_id)
    return client


def retrieve_client_by_email_service(
    session: Session, client_email: EmailStr
) -> Client:
    client = get_client_by_email(session, client_email)
    if client is None:
        raise ClientNotFoundByEmailError(client_email)
    return client


def list_clients_service(
    session: Session, offset: int = 0, limit: int = 100
) -> list[Client]:
    _validate_pagination(offset, limit)
    return get_clients(session, offset=offset, limit=limit)


def search_client_service(
    session: Session,
    params: ClientSearchParams,
    offset: int = 0,
    limit: int = 50,
) -> list[Client]:
    _validate_pagination(offset, limit)
    return search_client(session, params, limit=limit, offset=offset)


def update_client_service(
    session: Session, client_id: int, client_new_data_in: ClientUpdate
) -> Client:
    update_data = client_new_data_in.model_dump(exclude_unset=True)
    for field in ("name", "email", "phone_number"):
        if field in update_data and update_data[field] is None:
            raise ValueError(f"Client {field} cannot be null")

    updated = update_client(session, client_id, client_new_data_in)

    if updated is None:
        raise ClientNotFoundForUpdate(client_id, client_new_data_in)
    return updated


def delete_client_service(session: Session, client_id: int) -> bool:
    try:
        deleted = delete_client(session, client_id)
    except IntegrityError as exc:
        session.rollback()
        raise ClientHasOrdersError(client_id) from exc

    if not deleted:
        raise ClientNotFoundByIdError(client_id)
    return True


def _validate_pagination(offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    if limit < 1:
        raise ValueError("Limit must be at least 1")
