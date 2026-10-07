"""HTTP contract and inventory workflow tests against an isolated database."""
from decimal import Decimal

import pytest


def create_client(api, email="ana@example.com"):
    response = api.post("/clients/", json={
        "name": "Ana", "last_name": "Rivera", "email": email,
        "phone_number": "+14155552671", "address": "123 Main St", "city": "Miami", "state": "FL", "country": "US", "zipcode": "33101", "password": "test-password",
    })
    assert response.status_code == 201, response.text
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()
    return response.json()


def create_product(api):
    response = api.post("/products/", json={
        "name": " Coffee ", "description": "Ground", "price": "12.50", "quantity": 10,
    })
    assert response.status_code == 201, response.text
    return response.json()


def create_order(api, client_id, product_id, quantity=2):
    response = api.post("/orders/", json={
        "client_id": client_id,
        "products": [{"product_id": product_id, "quantity": quantity}],
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_client_crud_search_and_email_conflicts(api):
    client = create_client(api)
    path = f"/clients/{client['id']}"
    assert api.get(path).json() == client
    assert api.get("/clients/").json() == [client]
    assert api.get("/clients/search", params={"name": "An"}).json() == [client]
    assert api.get("/clients/search", params={"name": "Nobody"}).json() == []
    assert api.get("/clients/by-email", params={"email": client["email"]}).json() == client
    assert api.get("/clients/by-email", params={"email": "missing@example.com"}).status_code == 404
    assert api.post("/clients/", json={**client, "address": "123 Main St", "city": "Miami", "state": "FL", "country": "US", "zipcode": "33101", "password": "test-password"}).status_code == 409
    updated = api.put(path, json={"name": "Anita"})
    assert updated.status_code == 200
    assert updated.json()["id"] == client["id"]
    assert updated.json()["name"] == "Anita"
    assert updated.json()["email"] == client["email"]
    second = create_client(api, "second@example.com")
    assert api.put(path, json={"email": second["email"]}).status_code == 409
    assert api.get(path).json()["email"] == client["email"]
    deleted = api.delete(path)
    assert deleted.status_code == 200
    assert deleted.json() == {"id": client["id"]}
    assert api.get(path).status_code == 404


def test_product_crud_and_pagination(api):
    product = create_product(api)
    path = f"/products/{product['id']}"
    assert product["name"] == "Coffee"
    assert api.get(path).json() == product
    assert api.get("/products/", params={"limit": 1}).json() == [product]
    assert api.get("/products/", params={"offset": 1}).json() == []
    updated = api.put(path, json={"price": "15.25", "description": None})
    assert updated.status_code == 200
    assert Decimal(updated.json()["price"]) == Decimal("15.25")
    assert updated.json()["description"] is None
    assert updated.json()["quantity"] == 10
    assert api.delete(path).json() == {"id": product["id"]}
    assert api.get(path).status_code == 404


def test_order_and_items_adjust_inventory_and_protect_related_records(api):
    client = create_client(api)
    product = create_product(api)
    order = create_order(api, client["id"], product["id"])
    path = f"/orders/{order['id']}"
    product_path = f"/products/{product['id']}"
    assert Decimal(order["total"]) == Decimal("25")
    assert api.get(path).json() == order
    assert api.get("/orders/").json() == [order]
    assert api.get(product_path).json()["quantity"] == 8
    assert api.delete(f"/clients/{client['id']}").status_code == 409
    assert api.delete(product_path).status_code == 409
    items = api.get(f"{path}/items").json()
    assert len(items) == 1
    assert items[0]["quantity"] == 2
    added = api.post(f"{path}/items", json={"product_id": product["id"], "quantity": 1})
    assert added.status_code == 201
    assert added.json()["id"] == items[0]["id"]
    assert added.json()["quantity"] == 3
    assert Decimal(api.get(path).json()["total"]) == Decimal("37.50")
    assert api.get(product_path).json()["quantity"] == 7
    second_client = create_client(api, "second@example.com")
    updated = api.put(path, json={"client_id": second_client["id"]})
    assert updated.status_code == 200
    assert updated.json()["client_id"] == second_client["id"]
    removed = api.delete(f"{path}/items/{items[0]['id']}")
    assert removed.status_code == 200
    assert removed.json() == {"id": items[0]["id"]}
    assert api.get(f"{path}/items").json() == []
    assert Decimal(api.get(path).json()["total"]) == 0
    assert api.get(product_path).json()["quantity"] == 10
    assert api.post(f"{path}/items", json={"product_id": product["id"], "quantity": 4}).status_code == 201
    assert api.delete(path).json() == {"id": order["id"]}
    assert api.get(product_path).json()["quantity"] == 10
    assert api.get(path).status_code == 404


def test_cannot_delete_item_through_another_order(api):
    client = create_client(api)
    product = create_product(api)
    first = create_order(api, client["id"], product["id"])
    second = create_order(api, client["id"], product["id"])
    item = api.get(f"/orders/{first['id']}/items").json()[0]
    assert api.delete(f"/orders/{second['id']}/items/{item['id']}").status_code == 404
    assert api.get(f"/orders/{first['id']}/items").json() == [item]
    assert api.get(f"/products/{product['id']}").json()["quantity"] == 6


def test_order_failures_do_not_change_stock(api):
    client = create_client(api)
    product = create_product(api)
    payload = {"client_id": client["id"], "products": []}
    assert api.post("/orders/", json=payload).status_code == 422
    for quantity, status in [(0, 422), (-1, 422), (11, 409)]:
        payload["products"] = [{"product_id": product["id"], "quantity": quantity}]
        assert api.post("/orders/", json=payload).status_code == status
    payload["products"] = [{"product_id": 999, "quantity": 1}]
    assert api.post("/orders/", json=payload).status_code == 404
    payload["products"] = [{"product_id": product["id"], "quantity": 1}]
    payload["client_id"] = 999
    assert api.post("/orders/", json=payload).status_code == 404
    assert api.get("/orders/").json() == []
    assert api.get(f"/products/{product['id']}").json()["quantity"] == 10
    order = create_order(api, client["id"], product["id"])
    path = f"/orders/{order['id']}"
    assert api.post(f"{path}/items", json={"product_id": product["id"], "quantity": 9}).status_code == 409
    assert api.post(f"{path}/items", json={"product_id": product["id"], "quantity": 0}).status_code == 422
    assert api.post(f"{path}/items", json={"product_id": 999, "quantity": 1}).status_code == 404
    assert api.put(path, json={"client_id": 999}).status_code == 404
    assert api.get(path).json() == order
    assert api.get(f"/products/{product['id']}").json()["quantity"] == 8


@pytest.mark.parametrize("resource", ["clients", "products", "orders"])
@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_resources(api, resource, method):
    kwargs = {"json": {}} if method == "put" else {}
    assert getattr(api, method)(f"/{resource}/999", **kwargs).status_code == 404


@pytest.mark.parametrize("resource", ["clients", "products", "orders"])
@pytest.mark.parametrize("query", [{"offset": -1}, {"limit": 0}, {"limit": 101}])
def test_pagination_validation(api, resource, query):
    assert api.get(f"/{resource}/", params=query).status_code == 422


@pytest.mark.parametrize("path", ["/clients/0", "/products/-1", "/orders/abc"])
def test_id_validation(api, path):
    assert api.get(path).status_code == 422


@pytest.mark.parametrize("path,payload", [
    ("/clients/", {"email": "invalid"}),
    ("/products/", {"name": "   ", "price": "1", "quantity": 0}),
    ("/products/", {"name": "Coffee", "price": "-1", "quantity": 0}),
    ("/products/", {"name": "Coffee", "price": "1", "quantity": -1}),
    ("/orders/", {}),
])
def test_invalid_create_payloads(api, path, payload):
    assert api.post(path, json=payload).status_code == 422


def test_invalid_updates_and_search(api):
    client = create_client(api)
    product = create_product(api)
    order = create_order(api, client["id"], product["id"])
    assert api.put(f"/clients/{client['id']}", json={"name": None}).status_code == 422
    assert api.put(f"/products/{product['id']}", json={"quantity": None}).status_code == 422
    assert api.put(f"/orders/{order['id']}", json={"client_id": None}).status_code == 422
    assert api.get("/clients/search", params={"email": "invalid"}).status_code == 422
    assert api.get("/clients/search", params={"phone_number": "invalid"}).status_code == 422
    assert api.get("/clients/by-email", params={"email": "invalid"}).status_code == 422


def test_openapi_exposes_request_schemas_and_item_routes(api):
    response = api.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for resource in ["clients", "products", "orders"]:
        assert "requestBody" in paths[f"/{resource}/"]["post"]
    assert "delete" in paths["/products/{product_id}"]
    assert "post" in paths["/orders/{order_id}/items"]
