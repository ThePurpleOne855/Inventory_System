from fastapi import APIRouter, Depends

from app.core.auth import require_operator

from .analytics import router as analytics_router
from .auth import router as auth_router
from .clients import router as client_router
from .invoices import router as invoice_router
from .messages import router as message_router
from .orders import router as order_router
from .products import router as product_router

api_router = APIRouter()
# /auth handles its own credentials; everything else requires a logged-in operator.
api_router.include_router(auth_router)
operator_only = [Depends(require_operator)]
api_router.include_router(client_router, dependencies=operator_only)
api_router.include_router(order_router, dependencies=operator_only)
api_router.include_router(product_router, dependencies=operator_only)
api_router.include_router(invoice_router, dependencies=operator_only)
api_router.include_router(message_router, dependencies=operator_only)
api_router.include_router(analytics_router, dependencies=operator_only)
