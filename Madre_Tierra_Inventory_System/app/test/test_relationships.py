from sqlalchemy.orm import configure_mappers

def test_client_order_mapping():
    from app.models.client import Client
    from app.models.order import Order

    configure_mappers()

    assert "orders" in Client.__mapper__.relationships
    assert "client" in Order.__mapper__.relationships
