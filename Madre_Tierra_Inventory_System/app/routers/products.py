from fastapi import APIRouter, FastAPI

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

router.get("/")
def list_products():
    pass

@router.get("/{product_id}")
def get_product(product_id: int):
    pass

@router.post("/", status_code=201, responses={409: {"description": "Product already exists"} })
def create_product():
    pass

@router.put("/{product_id}")
def update_product(product_id: int):
    pass