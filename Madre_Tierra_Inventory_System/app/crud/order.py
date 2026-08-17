from typing import Optional
from sqlmodel import Session, select
from app.schema.order import OrderUpdate
from app.models.order import Order

def create_order(session: Session, order_data: Order) -> Order:
    session.add(order_data)
    session.commit()
    session.refresh(order_data)
    return order_data
    

def get_order(session: Session, order_id: int) -> Optional[Order]:
    return session.get(Order, order_id)

def get_orders(session: Session, offset: int = 0, limit: int = 100) -> list[Order]:
    statement = select(Order).offset(offset).limit(limit)
    return list(session.exec(statement).all())

def update_order(session: Session, order_id: int, order_in: OrderUpdate) -> Optional[Order]:
    order_obj = session.get(Order, order_id)

    if not order_obj:
        return None

    update_order_data = order_in.model_dump(exclude_unset=True)
    order_obj.sqlmodel_update(update_order_data)
    session.add(order_obj)
    session.commit()
    session.refresh(order_obj)
    return order_obj

def delete_order(session: Session, order_id: int) -> bool:
    order_obj = session.get(Order, order_id)

    if not order_obj:
        return False

    session.delete(order_obj)
    session.commit()
    return True 