"""Manual orders save customer details and stock in one transaction."""
from decimal import Decimal

import pytest


@pytest.fixture
def product(api):
    response = api.post('/products/', json={
        'name': 'Connecticut Toro', 'price': '12.50', 'quantity': 10,
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def details():
    return {
        'name': 'Ana', 'last_name': 'Rivera', 'email': 'ana@example.com',
        'phone_number': '+14155552671', 'address': '123 Main St',
        'city': 'Miami', 'state': 'FL', 'country': 'US', 'zipcode': '33101',
    }


def test_manual_order_creates_profile_and_deducts_stock(api, product, details):
    response = api.post('/orders/', json={
        'client': details, 'products': [{'product_id': product['id'], 'quantity': 2}],
    })
    assert response.status_code == 201, response.text
    order = response.json()
    assert Decimal(order['total']) == Decimal('25')
    clients = api.get('/clients/').json()
    assert len(clients) == 1
    assert clients[0]['id'] == order['client_id']
    assert clients[0]['address'] == details['address']
    assert 'hashed_password' not in clients[0]
    assert api.get(f"/products/{product['id']}").json()['quantity'] == 8
    invoice = api.get(f"/invoices/{order['id']}").json()
    assert invoice['client']['address'] == details['address']
    pdf = api.get(f"/invoices/{order['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b'%PDF')


def test_manual_order_reuses_selected_profile_and_updates_details(api, product, details):
    client = api.post('/clients/', json={**details, 'password': 'test-password'}).json()
    response = api.post('/orders/', json={
        'client_id': client['id'], 'client': {**details, 'address': '456 New Street'},
        'products': [{'product_id': product['id'], 'quantity': 1}],
    })
    assert response.status_code == 201, response.text
    assert response.json()['client_id'] == client['id']
    clients = api.get('/clients/').json()
    assert len(clients) == 1
    assert clients[0]['address'] == '456 New Street'


@pytest.mark.parametrize('existing', [False, True])
def test_failed_order_does_not_save_client_changes(api, product, details, existing):
    payload = {'client': {**details, 'address': 'Should not be saved'}}
    if existing:
        client = api.post('/clients/', json={**details, 'password': 'test-password'}).json()
        payload['client_id'] = client['id']
    response = api.post('/orders/', json={
        **payload, 'products': [{'product_id': product['id'], 'quantity': 11}],
    })
    assert response.status_code == 409
    clients = api.get('/clients/').json()
    assert len(clients) == int(existing)
    if existing:
        assert clients[0]['address'] == details['address']
    assert api.get('/orders/').json() == []
    assert api.get(f"/products/{product['id']}").json()['quantity'] == 10


def test_duplicate_email_does_not_create_another_profile(api, product, details):
    api.post('/clients/', json={**details, 'password': 'test-password'})
    response = api.post('/orders/', json={
        'client': {**details, 'email': 'ANA@example.com'},
        'products': [{'product_id': product['id'], 'quantity': 1}],
    })
    assert response.status_code == 409
    assert len(api.get('/clients/').json()) == 1
    assert api.get('/orders/').json() == []
    assert api.get(f"/products/{product['id']}").json()['quantity'] == 10


@pytest.mark.parametrize('field,value', [('name', '  '), ('email', 'invalid'), ('phone_number', 'bad')])
def test_manual_order_validates_contact_details(api, product, details, field, value):
    response = api.post('/orders/', json={
        'client': {**details, field: value},
        'products': [{'product_id': product['id'], 'quantity': 1}],
    })
    assert response.status_code == 422
    assert api.get('/clients/').json() == []


@pytest.mark.parametrize('field', ['address', 'city', 'state', 'country', 'zipcode'])
@pytest.mark.parametrize('value', [None, '', '   '])
def test_new_clients_require_complete_addresses(api, product, details, field, value):
    incomplete = {**details, field: value}
    direct = api.post('/clients/', json={**incomplete, 'password': 'test-password'})
    assert direct.status_code == 422
    order = api.post('/orders/', json={
        'client': incomplete,
        'products': [{'product_id': product['id'], 'quantity': 1}],
    })
    assert order.status_code == 422
    assert api.get('/clients/').json() == []


def test_structured_address_roundtrip(api, details):
    response = api.post('/clients/', json={**details, 'password': 'test-password'})
    assert response.status_code == 201, response.text
    saved = response.json()
    for field in ('address', 'city', 'state', 'country', 'zipcode'):
        assert saved[field] == details[field]
    updated = api.put(f"/clients/{saved['id']}", json={'city': 'Orlando', 'zipcode': '03280'})
    assert updated.status_code == 200
    assert updated.json()['city'] == 'Orlando'
    assert updated.json()['zipcode'] == '03280'
