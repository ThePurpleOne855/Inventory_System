from fastapi import FastAPI, APIRouter


router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@router.get("/")
def list_orders():
    pass

@router.get("/{order_id}")
def get_order(order_id: int):
    pass

@router.post("/")
def create_order():
    pass

@router.put("/{order_id}")
def update_order(order_id: int):
    pass

@router.delete("/{order_id}")
def delete_order(order_id: int):
    pass
