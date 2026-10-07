from fastapi import APIRouter

from app.routers.dependencies import (
    Limit,
    Offset,
    PositiveId,
    SessionDep,
    service_errors,
)
from app.schema.product import ProductCreate, ProductDelete, ProductRead, ProductUpdate
from app.service import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductRead])
def list_products(session: SessionDep, offset: Offset = 0, limit: Limit = 100):
    with service_errors():
        return product_service.list_products_service(
            session, offset=offset, limit=limit
        )


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: PositiveId, session: SessionDep):
    with service_errors():
        return product_service.retrieve_product_by_id_service(session, product_id)


@router.post("/", status_code=201, response_model=ProductRead)
def create_product(product: ProductCreate, session: SessionDep):
    with service_errors():
        return product_service.register_product_service(session, product)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: PositiveId, product: ProductUpdate, session: SessionDep):
    with service_errors():
        return product_service.update_product_service(session, product_id, product)


@router.delete("/{product_id}", response_model=ProductDelete)
def delete_product(product_id: PositiveId, session: SessionDep):
    with service_errors():
        product_service.delete_product_service(session, product_id)
    return ProductDelete(id=product_id)
