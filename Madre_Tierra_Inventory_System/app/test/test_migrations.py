"""Exercise the real migrations instead of creating tables from model metadata."""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import event, inspect
from sqlmodel import create_engine


@pytest.fixture
def db_engine(auth_environment, tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    command.upgrade(config, 'head')
    engine = create_engine(url, connect_args={'check_same_thread': False})

    @event.listens_for(engine, 'connect')
    def enable_foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

    yield engine
    engine.dispose()


def test_migrated_database_supports_manual_orders(api, db_engine):
    assert 'orderproduct' in inspect(db_engine).get_table_names()
    product = api.post('/products/', json={'name': 'Migration test', 'price': '12.50', 'quantity': 3}).json()
    response = api.post('/orders/', json={
        'client': {
            'name': 'Migration', 'email': 'migration@example.com',
            'phone_number': '+14155552671', 'address': '123 Main St',
            'city': 'Miami', 'state': 'FL', 'country': 'US', 'zipcode': '33101',
        },
        'products': [{'product_id': product['id'], 'quantity': 2}],
    })
    assert response.status_code == 201, response.text
    order_id = response.json()['id']
    assert len(api.get(f'/orders/{order_id}/items').json()) == 1
    assert api.get(f"/products/{product['id']}").json()['quantity'] == 1
    assert api.get(f'/invoices/{order_id}/pdf').status_code == 200
    assert api.delete(f'/orders/{order_id}').status_code == 200
    assert api.get(f"/products/{product['id']}").json()['quantity'] == 3
