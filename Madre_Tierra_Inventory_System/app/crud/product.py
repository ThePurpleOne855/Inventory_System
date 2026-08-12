from typing import Optional
from sqlmodel import Session, select
from schema.product import ProductUpdate
from models.product import  Product


def create_product(session: Session, product_data: Product) -> Product:
    session.add(product_data)
    session.commit()
    session.refresh(product_data)
    return product_data

def get_product(session: Session, product_id) -> Optional[Product]:
    return session.get(Product, product_id)
    
def get_products(session: Session, offset: int = 0, limit: int = 100) -> list[Product]:
    statement = select(Product).offset(offset).limit(limit)
    return list(session.exec(statement).all())

def update_product(session: Session, product_id: int, product_in: ProductUpdate) -> Optional[Product]:
    product_obj = session.get(Product, product_id)

    if not product_obj:
        return None

    update_product_data = product_in.model_dump(exclude_unset=True)
    product_obj.sqlmodel_update(update_product_data)
    session.add(product_obj)
    session.commit()
    session.refresh(product_obj)
    return product_obj
    
def delete_product(session: Session, product_id: int) -> bool:
    product_obj = session.get(Product, product_id)

    if not product_obj:
        return False

    session.delete(product_obj)
    session.commit()
    return True
    
