from sqlmodel import Session

from app.crud.order import get_order
from app.crud.order_product import (
    create_order_product,
    delete_order_product,
    get_order_product,
    get_order_products_for_order,
)
from app.crud.product import get_product
from app.models.order_product import OrderProduct
from app.schema.order_product import OrderProductCreate
from app.service.order_exceptions import OrderNotFoundError, ProductNotFoundError


def create_order_product_service(
    session: Session, order_product_data: OrderProduct
) -> OrderProduct:
    return create_order_product(session, order_product_data)


def get_order_products_for_order_service(session, order_id) -> list[OrderProduct]:
    return get_order_products_for_order(session, order_id)


def add_item_to_order_service(
    session: Session, order_id: int, item_in: OrderProductCreate
) -> OrderProduct:
    if get_order(session, order_id) is None:
        raise OrderNotFoundError(order_id)

    product = get_product(session, item_in.product_id)
    if product is None:
        raise ProductNotFoundError(item_in.product_id)

    existing = get_order_product(session, order_id, item_in.product_id)

    if existing is not None:
        existing.quantity += item_in.quantity
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    new_item = OrderProduct(
        order_id=order_id,
        product_id=item_in.product_id,
        quantity=item_in.quantity,
        unit_price=product.price,
    )

    return create_order_product(session, new_item)


def delete_order_product_service(session: Session, order_product_id) -> bool:
    return delete_order_product(session, order_product_id)
