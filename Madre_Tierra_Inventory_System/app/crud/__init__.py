from .client import create_client, get_client_by_email, get_client_by_id, get_clients, update_client, delete_client, search_client
from .order import create_order, get_order, get_orders, update_order, delete_client
from .product import create_product, get_product, get_products, update_product, delete_product

_all__ = [
    #Client Crud
    "create_client", "get_client_by_email",
    "get_client_by_id", "get_clients",
    "update_client", "delete_client",
    "search_client",

    #Client Crud
    "create_order", "get_order",
    "get_orders", "update_order", "delete_client",

    #Product Crud
    "create_product", "get_product",
    "get_products", "update_product", "delete_product"

    ]


