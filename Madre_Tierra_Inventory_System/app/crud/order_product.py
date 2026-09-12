from sqlmodel import Session, select

from app.models.order_product import OrderProduct


def create_order_product(
    session: Session, order_product_data: OrderProduct
) -> OrderProduct:
    session.add(order_product_data)
    session.commit()
    session.refresh(order_product_data)
    return order_product_data


def get_order_products_for_order(session: Session, order_id: int) -> list[OrderProduct]:
    statement = select(OrderProduct).where(OrderProduct.order_id == order_id)
    return list(session.exec(statement).all())


def get_order_product(session: Session, order_id: int, product_id):
    statement = select(OrderProduct).where(
        OrderProduct.order_id == order_id, OrderProduct.product_id == product_id
    )
    return session.exec(statement).first()


def delete_order_product(session: Session, order_product_id: int) -> bool:
    order_product_obj = session.get(OrderProduct, order_product_id)

    if not order_product_obj:
        return False

    session.delete(order_product_obj)
    session.commit()
    return True
