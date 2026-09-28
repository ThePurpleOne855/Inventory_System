from decimal import Decimal

from sqlmodel import Session

from app.crud.client import get_client_by_id
from app.crud.order import get_order, get_orders, update_order
from app.crud.order_product import (
    get_order_product,
    get_order_product_by_id,
    get_order_products_for_order,
)
from app.crud.product import get_product
from app.models.order import Order
from app.models.order_product import OrderProduct
from app.schema.order import OrderCreate, OrderUpdate
from app.schema.order_product import OrderProductCreate
from app.service.client_exceptions import ClientNotFoundByIdError
from app.service.order_exceptions import (
    InsufficientProductStockError,
    InvalidOrderQuantityError,
    OrderNotFoundError,
    OrderProductNotFoundError,
    ProductNotFoundError,
)


def create_order_service(session: Session, order_in: OrderCreate) -> Order:
    if get_client_by_id(session, order_in.client_id) is None:
        raise ClientNotFoundByIdError(order_in.client_id)
    if not order_in.products:
        raise ValueError("An order must contain at least one product")

    quantities: dict[int, int] = {}
    for item in order_in.products:
        if item.quantity <= 0:
            raise InvalidOrderQuantityError(item.product_id, item.quantity)
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity

    products = {}
    total = Decimal("0")
    for product_id, quantity in quantities.items():
        product = get_product(session, product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        if product.quantity < quantity:
            raise InsufficientProductStockError(
                product_id, requested=quantity, available=product.quantity
            )
        products[product_id] = product
        total += product.price * quantity

    order = Order(client_id=order_in.client_id, total=float(total))
    try:
        session.add(order)
        session.flush()
        if order.id is None:
            raise RuntimeError("The database did not assign an order id")

        for product_id, quantity in quantities.items():
            product = products[product_id]
            product.quantity -= quantity
            session.add(product)
            session.add(
                OrderProduct(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=product.price,
                )
            )

        session.commit()
        session.refresh(order)
    except Exception:
        session.rollback()
        raise
    return order


def list_orders_service(
    session: Session, offset: int = 0, limit: int = 100
) -> list[Order]:
    _validate_pagination(offset, limit)
    return get_orders(session, offset=offset, limit=limit)


def retrieve_order_by_id_service(session: Session, order_id: int) -> Order:
    order = get_order(session, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


def update_order_service(
    session: Session, order_id: int, order_in: OrderUpdate
) -> Order:
    update_data = order_in.model_dump(exclude_unset=True)
    if "client_id" in update_data and update_data["client_id"] is None:
        raise ValueError("Order client_id cannot be null")
    if update_data.get("client_id") is not None and get_client_by_id(
        session, update_data["client_id"]
    ) is None:
        raise ClientNotFoundByIdError(update_data["client_id"])

    order = update_order(session, order_id, order_in)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


def delete_order_service(session: Session, order_id: int) -> bool:
    order = get_order(session, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)

    items = get_order_products_for_order(session, order_id)
    products = []
    for item in items:
        product = get_product(session, item.product_id)
        if product is None:
            raise ProductNotFoundError(item.product_id)
        products.append((item, product))

    try:
        for item, product in products:
            product.quantity += item.quantity
            session.add(product)
            session.delete(item)
        session.delete(order)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return True


def create_order_product_service(
    session: Session, order_product_data: OrderProduct
) -> OrderProduct:
    return add_item_to_order_service(
        session,
        order_product_data.order_id,
        OrderProductCreate(
            product_id=order_product_data.product_id,
            quantity=order_product_data.quantity,
        ),
    )


def get_order_products_for_order_service(
    session: Session, order_id: int
) -> list[OrderProduct]:
    if get_order(session, order_id) is None:
        raise OrderNotFoundError(order_id)
    return get_order_products_for_order(session, order_id)


def add_item_to_order_service(
    session: Session, order_id: int, item_in: OrderProductCreate
) -> OrderProduct:
    order = get_order(session, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    if item_in.quantity <= 0:
        raise InvalidOrderQuantityError(item_in.product_id, item_in.quantity)

    product = get_product(session, item_in.product_id)
    if product is None:
        raise ProductNotFoundError(item_in.product_id)
    if product.quantity < item_in.quantity:
        raise InsufficientProductStockError(
            item_in.product_id,
            requested=item_in.quantity,
            available=product.quantity,
        )

    existing = get_order_product(session, order_id, item_in.product_id)
    if existing is None:
        order_product = OrderProduct(
            order_id=order_id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_price=product.price,
        )
        price_delta = product.price * item_in.quantity
    else:
        order_product = existing
        order_product.quantity += item_in.quantity
        price_delta = order_product.unit_price * item_in.quantity

    product.quantity -= item_in.quantity
    order.total = float(Decimal(str(order.total)) + price_delta)
    try:
        session.add(product)
        session.add(order)
        session.add(order_product)
        session.commit()
        session.refresh(order_product)
    except Exception:
        session.rollback()
        raise
    return order_product


def delete_order_product_service(session: Session, order_product_id: int) -> bool:
    item = get_order_product_by_id(session, order_product_id)
    if item is None:
        raise OrderProductNotFoundError(order_product_id)

    order = get_order(session, item.order_id)
    if order is None:
        raise OrderNotFoundError(item.order_id)
    product = get_product(session, item.product_id)
    if product is None:
        raise ProductNotFoundError(item.product_id)

    product.quantity += item.quantity
    order.total = float(
        Decimal(str(order.total)) - item.unit_price * item.quantity
    )
    try:
        session.add(product)
        session.add(order)
        session.delete(item)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return True


def _validate_pagination(offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    if limit < 1:
        raise ValueError("Limit must be at least 1")
