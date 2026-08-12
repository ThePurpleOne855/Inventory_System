from fastapi import FastAPI, APIRouter

from Madre_Tierra_Inventory_System.app.schema.client import ClientUpdate
from Madre_Tierra_Inventory_System.app.schema.order import OrderDelete, OrderRead


router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@router.get("/", response_model=list[OrderRead])
def list_orders():
    pass

@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int):
    pass

@router.post("/", response_model=OrderRead, status_code = 201)
def create_order():
    pass

@router.put("/{order_id}", response_model=OrderRead)
def update_order(order_id: int, client: ClientUpdate):
    pass

@router.delete("/{order_id}", response_model=OrderDelete)
def delete_order(order_id: int):
    pass
