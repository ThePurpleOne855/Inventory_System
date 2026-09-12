from .client import (
    create_client,
    delete_client,
    get_client_by_email,
    get_client_by_id,
    get_clients,
    search_client,
    update_client,
)
from .order import create_order, delete_order, get_order, get_orders, update_order
from .order_product import (
    create_order_product,
    delete_order_product,
    get_order_products_for_order,
)
from .product import (
    create_product,
    delete_product,
    get_product,
    get_products,
    update_product,
)

__all__ = [
    # Client Crud
    "create_client",
    # Order Crud
    "create_order",
    # OrderProduct Crud
    "create_order_product",
    # Product Crud
    "create_product",
    "delete_client",
    "delete_order",
    "delete_order_product",
    "delete_product",
    "get_client_by_email",
    "get_client_by_id",
    "get_clients",
    "get_order",
    "get_order_products_for_order",
    "get_orders",
    "get_product",
    "get_products",
    "search_client",
    "update_client",
    "update_order",
    "update_product",
]
