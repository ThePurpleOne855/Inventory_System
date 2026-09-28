from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.crud.product import (
    create_product,
    delete_product,
    get_product,
    get_products,
    update_product,
)
from app.models.product import Product
from app.schema.product import ProductCreate, ProductUpdate
from app.service.product_exceptions import ProductInUseError, ProductNotFoundError


def register_product_service(session: Session, product_in: ProductCreate) -> Product:
    if not product_in.name.strip():
        raise ValueError("Product name cannot be blank")
    _validate_product_values(
        price=product_in.price,
        quantity=product_in.quantity,
    )

    product = Product(
        name=product_in.name.strip(),
        description=product_in.description,
        price=product_in.price,
        quantity=product_in.quantity,
    )
    return create_product(session, product)


def list_products_service(
    session: Session, offset: int = 0, limit: int = 100
) -> list[Product]:
    _validate_pagination(offset, limit)
    return get_products(session, offset=offset, limit=limit)


def retrieve_product_by_id_service(session: Session, product_id: int) -> Product:
    product = get_product(session, product_id)
    if product is None:
        raise ProductNotFoundError(product_id)
    return product


def update_product_service(
    session: Session, product_id: int, product_in: ProductUpdate
) -> Product:
    update_data = product_in.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is None:
        raise ValueError("Product name cannot be null")
    if "name" in update_data:
        update_data["name"] = update_data["name"].strip()
        if not update_data["name"]:
            raise ValueError("Product name cannot be blank")
    for field in ("price", "quantity"):
        if field in update_data and update_data[field] is None:
            raise ValueError(f"Product {field} cannot be null")

    _validate_product_values(
        price=update_data.get("price"),
        quantity=update_data.get("quantity"),
    )

    updated = update_product(
        session,
        product_id,
        ProductUpdate.model_validate(update_data),
    )
    if updated is None:
        raise ProductNotFoundError(product_id)
    return updated


def delete_product_service(session: Session, product_id: int) -> bool:
    try:
        deleted = delete_product(session, product_id)
    except IntegrityError as exc:
        session.rollback()
        raise ProductInUseError(product_id) from exc

    if not deleted:
        raise ProductNotFoundError(product_id)
    return True


def _validate_product_values(
    price: Decimal | None = None, quantity: int | None = None
) -> None:
    if price is not None and price < 0:
        raise ValueError("Product price cannot be negative")
    if quantity is not None and quantity < 0:
        raise ValueError("Product quantity cannot be negative")


def _validate_pagination(offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    if limit < 1:
        raise ValueError("Limit must be at least 1")
