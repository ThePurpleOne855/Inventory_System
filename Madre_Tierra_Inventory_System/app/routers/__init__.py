from fastapi import APIRouter
from .clients import router as client_router
from .orders import router as order_router
from .products import router as product_router

api_router = APIRouter()
api_router.include_router(client_router)
api_router.include_router(order_router)
api_router.include_router(product_router)
