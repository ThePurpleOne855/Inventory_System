"""Cancelled orders, exact money, client source, and the dashboard summary."""
from datetime import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session

from app.core.config import settings
from app.models import Order


def client_details(email, source=None):
    return {
        'name': 'Ana', 'last_name': 'Rivera', 'email': email,
        'phone_number': '+14155552671', 'address': '123 Main St',
        'city': 'Miami', 'state': 'FL', 'country': 'US', 'zipcode': '33101',
        'source': source,
    }


def add_product(api, name, price, quantity):
    response = api.post('/products/', json={'name': name, 'price': price, 'quantity': quantity})
    assert response.status_code == 201, response.text
    return response.json()['id']


def place_order(api, db_engine, when, products, client=None, client_id=None):
    response = api.post('/orders/', json={
        'client': client, 'client_id': client_id,
        'products': [{'product_id': pid, 'quantity': qty} for pid, qty in products],
    })
    assert response.status_code == 201, response.text
    order = response.json()
    with Session(db_engine) as session:
        stored = session.get(Order, order['id'])
        stored.created_at = when
        session.add(stored)
        session.commit()
    return order


def test_order_totals_are_exact(api):
    product = add_product(api, 'Seeds', '0.10', 10)
    order = api.post('/orders/', json={
        'client': client_details('exact@example.com'),
        'products': [{'product_id': product, 'quantity': 3}],
    }).json()
    assert order['total'] == '0.30'


def test_cancel_returns_stock_and_keeps_the_order(api):
    product = add_product(api, 'Coffee', '10.00', 10)
    order = api.post('/orders/', json={
        'client': client_details('cancel@example.com'),
        'products': [{'product_id': product, 'quantity': 2}],
    }).json()
    assert api.get(f'/products/{product}').json()['quantity'] == 8

    response = api.post(f"/orders/{order['id']}/cancel")
    assert response.status_code == 200, response.text
    assert response.json()['cancelled_at'] is not None
    assert api.get(f'/products/{product}').json()['quantity'] == 10
    assert api.get(f"/orders/{order['id']}").status_code == 200

    assert api.post(f"/orders/{order['id']}/cancel").status_code == 409
    added = api.post(f"/orders/{order['id']}/items", json={'product_id': product, 'quantity': 1})
    assert added.status_code == 409

    # Deleting a cancelled order must not return its stock a second time.
    assert api.delete(f"/orders/{order['id']}").status_code == 200
    assert api.get(f'/products/{product}').json()['quantity'] == 10


def test_client_source_is_trimmed_and_limited(api):
    created = api.post('/clients/', json={
        **client_details('source@example.com', '  Instagram '), 'password': 'test-password',
    })
    assert created.status_code == 201, created.text
    assert created.json()['source'] == 'Instagram'
    too_long = api.post('/clients/', json={
        **client_details('long@example.com', 'x' * 51), 'password': 'test-password',
    })
    assert too_long.status_code == 422


@pytest.fixture
def new_york(monkeypatch):
    monkeypatch.setattr(settings, 'business_timezone', 'America/New_York')


def test_summary_counts_sales_customers_and_stock(api, db_engine, new_york):
    coffee = add_product(api, 'Coffee', '10.00', 100)
    tea = add_product(api, 'Tea', '4.50', 3)

    # Ana: first order in the previous period, buys again this period -> repeat customer.
    first = place_order(api, db_engine, datetime(2025, 12, 15, 15), [(coffee, 1)],
                        client=client_details('ana@example.com', 'Instagram'))
    place_order(api, db_engine, datetime(2026, 2, 10, 15), [(coffee, 2)],
                client_id=first['client_id'])
    # 03:00 UTC on Feb 1 is still Jan 31 in New York.
    place_order(api, db_engine, datetime(2026, 2, 1, 3), [(tea, 1)],
                client=client_details('ben@example.com', 'Website'))
    carla = place_order(api, db_engine, datetime(2026, 3, 5, 15), [(coffee, 3)],
                        client=client_details('carla@example.com'))
    cancelled = place_order(api, db_engine, datetime(2026, 3, 6, 15), [(coffee, 1)],
                            client_id=carla['client_id'])
    assert api.post(f"/orders/{cancelled['id']}/cancel").status_code == 200

    response = api.get('/analytics/summary', params={'start': '2026-01-01', 'end': '2026-03-31'})
    assert response.status_code == 200, response.text
    summary = response.json()

    current = summary['current']
    assert Decimal(current['revenue']) == Decimal('54.50')
    assert current['orders'] == 3
    assert Decimal(current['average_order']) == Decimal('18.17')
    assert (current['new_customers'], current['repeat_customers']) == (2, 1)
    assert current['cancelled_orders'] == 1

    previous = summary['previous']
    assert Decimal(previous['revenue']) == Decimal('10')
    assert (previous['orders'], previous['new_customers'], previous['repeat_customers']) == (1, 1, 0)

    assert [
        (month['month'], Decimal(month['revenue']), month['orders'], month['new_customers'])
        for month in summary['monthly']
    ] == [
        ('2026-01', Decimal('4.50'), 1, 1),
        ('2026-02', Decimal('20'), 1, 0),
        ('2026-03', Decimal('30'), 1, 1),
    ]

    assert [(p['name'], p['units'], Decimal(p['revenue'])) for p in summary['top_products']] == [
        ('Coffee', 5, Decimal('50')),
        ('Tea', 1, Decimal('4.50')),
    ]
    assert {s['source']: s['customers'] for s in summary['new_customers_by_source']} == {
        'Website': 1, 'Not recorded': 1,
    }
    assert [(s['name'], s['quantity']) for s in summary['low_stock']] == [('Tea', 2)]


def test_summary_defaults_to_twelve_months_and_rejects_reversed_range(api, new_york):
    summary = api.get('/analytics/summary').json()
    assert len(summary['monthly']) == 12
    assert summary['current']['orders'] == 0

    reversed_range = api.get('/analytics/summary', params={'start': '2026-03-01', 'end': '2026-01-01'})
    assert reversed_range.status_code == 422
