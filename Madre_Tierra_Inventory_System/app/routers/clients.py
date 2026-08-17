from fastapi import  APIRouter, HTTPException
from app.schema.client import ClientCreate, ClientDelete, ClientRead, ClientUpdate 

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/", response_model=list[ClientRead])
def list_clients():
    pass

@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: int):
    pass

@router.post("/", status_code=201, response_model=ClientRead)
def create_client(client: ClientCreate): 
    pass

@router.put("/{client_id}", response_model=ClientUpdate)
def update_client(client_id: int, client: ClientUpdate):
    pass

@router.delete("/{client_id}", response_model=ClientDelete)
def delete_client(client_id: int):
    pass