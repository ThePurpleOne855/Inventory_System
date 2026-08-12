from fastapi import APIRouter, FastAPI

from Madre_Tierra_Inventory_System.app.schema.product import ProductRead

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

router.get("/", response_model=list[ProductRead])
def list_products():
    pass

@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int):
    pass

@router.post("/", response_model=ProductRead, status_code=201, responses={409: {"description": "Product already exists"}})
def create_product():
    pass

@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: int):
    pass