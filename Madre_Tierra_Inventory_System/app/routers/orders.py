from fastapi import APIRouter

from app.routers.dependencies import (
    Limit,
    Offset,
    PositiveId,
    SessionDep,
    service_errors,
)
from app.schema.order import OrderCreate, OrderDelete, OrderRead, OrderUpdate
from app.schema.order_product import (
    OrderProductCreate,
    OrderProductDelete,
    OrderProductRead,
)
from app.service import order_service
from app.service.order_exceptions import OrderProductNotFoundError

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderRead])
def list_orders(session: SessionDep, offset: Offset = 0, limit: Limit = 100):
    with service_errors():
        return order_service.list_orders_service(session, offset=offset, limit=limit)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: PositiveId, session: SessionDep):
    with service_errors():
        return order_service.retrieve_order_by_id_service(session, order_id)


@router.post("/", status_code=201, response_model=OrderRead)
def create_order(order: OrderCreate, session: SessionDep):
    with service_errors():
        return order_service.create_order_service(session, order)


@router.put("/{order_id}", response_model=OrderRead)
def update_order(order_id: PositiveId, order: OrderUpdate, session: SessionDep):
    with service_errors():
        return order_service.update_order_service(session, order_id, order)


@router.delete("/{order_id}", response_model=OrderDelete)
def delete_order(order_id: PositiveId, session: SessionDep):
    with service_errors():
        order_service.delete_order_service(session, order_id)
    return OrderDelete(id=order_id)


@router.get("/{order_id}/items", response_model=list[OrderProductRead])
def list_order_items(order_id: PositiveId, session: SessionDep):
    with service_errors():
        return order_service.get_order_products_for_order_service(session, order_id)


@router.post("/{order_id}/items", response_model=OrderProductRead, status_code=201)
def add_order_item(order_id: PositiveId, item: OrderProductCreate, session: SessionDep):
    with service_errors():
        return order_service.add_item_to_order_service(session, order_id, item)


@router.delete("/{order_id}/items/{item_id}", response_model=OrderProductDelete)
def delete_order_item(order_id: PositiveId, item_id: PositiveId, session: SessionDep):
    with service_errors():
        items = order_service.get_order_products_for_order_service(session, order_id)
        if not any(item.id == item_id for item in items):
            raise OrderProductNotFoundError(item_id)
        order_service.delete_order_product_service(session, item_id)
    return OrderProductDelete(id=item_id)
