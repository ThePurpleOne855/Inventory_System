from fastapi import FastAPI, APIRouter
from app.schema.client import ClientCreate, ClientRead, ClientUpdate 


app = FastAPI()

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/")
def list_clients():
    pass

@router.get("/{client_id}")
def get_client(client_id: int):
    pass

@router.post("/", status_code=201, responses={409: {"description": "Client already exists"}})
def create_client(client: ClientCreate): 
    pass

@router.put("/{client_id}")
def update_client(client_id: int, client: ClientUpdate):
    pass

@router.delete("/{client_id}")
def delete_client(client_id: int):
    pass