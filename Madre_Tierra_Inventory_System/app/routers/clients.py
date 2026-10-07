from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import EmailStr

from app.routers.dependencies import (
    Limit,
    Offset,
    PositiveId,
    SessionDep,
    service_errors,
)
from app.schema.client import (
    ClientCreate,
    ClientDelete,
    ClientRead,
    ClientSearchParams,
    ClientUpdate,
)
from app.service import client_service

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=list[ClientRead])
def list_clients(session: SessionDep, offset: Offset = 0, limit: Limit = 100):
    with service_errors():
        return client_service.list_clients_service(session, offset=offset, limit=limit)


@router.get("/search", response_model=list[ClientRead])
def search_clients(
    session: SessionDep,
    params: Annotated[ClientSearchParams, Depends()],
    offset: Offset = 0,
    limit: Limit = 50,
):
    with service_errors():
        return client_service.search_client_service(
            session, params, offset=offset, limit=limit
        )


@router.get("/by-email", response_model=ClientRead)
def get_client_by_email(session: SessionDep, email: EmailStr):
    with service_errors():
        return client_service.retrieve_client_by_email_service(session, email)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: PositiveId, session: SessionDep):
    with service_errors():
        return client_service.retrieve_client_by_id_service(session, client_id)


@router.post("/", status_code=201, response_model=ClientRead)
def create_client(client: ClientCreate, session: SessionDep):
    with service_errors():
        return client_service.register_client_service(session, client)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(client_id: PositiveId, client: ClientUpdate, session: SessionDep):
    with service_errors():
        return client_service.update_client_service(session, client_id, client)


@router.delete("/{client_id}", response_model=ClientDelete)
def delete_client(client_id: PositiveId, session: SessionDep):
    with service_errors():
        client_service.delete_client_service(session, client_id)
    return ClientDelete(id=client_id)
