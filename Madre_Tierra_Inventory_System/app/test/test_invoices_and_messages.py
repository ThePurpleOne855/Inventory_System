"""Invoice generation and client messaging, including the SMTP boundary."""
import smtplib
from email import message_from_bytes

import pytest

from app.core import config


@pytest.fixture
def order(api):
    """One client, two products, and an order spending some of each."""
    client = api.post("/clients/", json={
        "name": "Ana", "last_name": "Gomez", "email": "ana@example.com",
        "phone_number": "+12125550123", "address": "123 Main St", "city": "Miami", "state": "FL", "country": "US", "zipcode": "33101", "password": "supersecret",
    }).json()
    first = api.post("/products/", json={
        "name": "Compost, 20 kg bag", "price": "18.50", "quantity": 40,
    }).json()
    second = api.post("/products/", json={
        "name": "Tomato seedlings", "price": "24.00", "quantity": 15,
    }).json()
    response = api.post("/orders/", json={"client_id": client["id"], "products": [
        {"product_id": first["id"], "quantity": 3},
        {"product_id": second["id"], "quantity": 2},
    ]})
    assert response.status_code == 201, response.text
    return {"client": client, "products": [first, second], "order": response.json()}


class FakeSMTP:
    """Stands in for smtplib.SMTP and records every message handed to it."""

    instances: list["FakeSMTP"] = []
    fail_for: set[str] = set()
    connect_error: Exception | None = None

    def __init__(self, host, port, timeout=None):
        if FakeSMTP.connect_error is not None:
            raise FakeSMTP.connect_error
        self.host, self.port = host, port
        self.sent: list = []
        self.logins: list = []
        self.started_tls = False
        self.quit_called = False
        FakeSMTP.instances.append(self)

    def ehlo(self):
        return 250, b"ok"

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logins.append((user, password))

    def send_message(self, message):
        if message["To"] in FakeSMTP.fail_for:
            raise smtplib.SMTPRecipientsRefused({message["To"]: (550, b"No such user")})
        self.sent.append(message)

    def quit(self):
        self.quit_called = True

    def close(self):
        pass


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.instances = []
    FakeSMTP.fail_for = set()
    FakeSMTP.connect_error = None
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(config.settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(config.settings, "smtp_port", 587)
    monkeypatch.setattr(config.settings, "smtp_user", "mailer@example.com")
    monkeypatch.setattr(config.settings, "smtp_password", "app-password")
    monkeypatch.setattr(config.settings, "smtp_from", "hola@madretierra.co")
    monkeypatch.setattr(config.settings, "smtp_starttls", True)
    return FakeSMTP


# --- Invoices ---------------------------------------------------------------

def test_invoice_reports_line_items_and_totals(api, order):
    invoice = api.get(f"/invoices/{order['order']['id']}").json()

    assert invoice["invoice_number"] == f"INV-{order['order']['id']:05d}"
    assert invoice["client"]["email"] == "ana@example.com"
    assert "hashed_password" not in invoice["client"]
    assert [(line["product_name"], line["quantity"]) for line in invoice["lines"]] == [
        ("Compost, 20 kg bag", 3), ("Tomato seedlings", 2),
    ]
    assert float(invoice["subtotal"]) == pytest.approx(103.5)
    assert float(invoice["total"]) == pytest.approx(103.5)


def test_invoice_keeps_the_price_charged_when_the_product_changes(api, order):
    product_id = order["products"][0]["id"]
    api.put(f"/products/{product_id}", json={"name": "Compost (renamed)", "price": "99.00"})

    invoice = api.get(f"/invoices/{order['order']['id']}").json()
    line = next(item for item in invoice["lines"] if item["product_id"] == product_id)
    assert line["product_name"] == "Compost (renamed)"
    assert float(line["unit_price"]) == pytest.approx(18.5)
    assert float(invoice["total"]) == pytest.approx(103.5)


def test_invoice_pdf_downloads_as_an_attachment(api, order):
    response = api.get(f"/invoices/{order['order']['id']}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "INV-00001.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


@pytest.mark.parametrize("path", ["/invoices/999", "/invoices/999/pdf"])
def test_invoice_for_a_missing_order_is_404(api, path):
    assert api.get(path).status_code == 404


# --- Messages ---------------------------------------------------------------

def test_status_and_broadcast_report_unconfigured_email(api):
    assert api.get("/messages/status").json()["configured"] is False
    response = api.post("/messages/broadcast", json={"subject": "Hi", "body": "Hello"})
    assert response.status_code == 503
    assert "SMTP_HOST" in response.json()["detail"]


def test_broadcast_personalises_and_sends_one_email_per_client(api, order, smtp):
    api.post("/clients/", json={
        "name": "Bruno", "last_name": "Diaz", "email": "bruno@example.com",
        "phone_number": "+573001112233", "address": "123 Main St", "city": "Miami", "state": "FL", "country": "US", "zipcode": "33101", "password": "supersecret",
    })

    response = api.post("/messages/broadcast", json={
        "subject": "Seedlings, {name}", "body": "Hi {full_name}, stock is in.",
    })

    assert response.status_code == 200
    assert response.json()["sent"] == 2
    assert response.json()["failed"] == 0

    sent = smtp.instances[0].sent
    assert [message["To"] for message in sent] == ["ana@example.com", "bruno@example.com"]
    assert sent[0]["Subject"] == "Seedlings, Ana"
    assert "Hi Ana Gomez" in sent[0].get_content()
    assert sent[1]["Subject"] == "Seedlings, Bruno"
    # One recipient per message, so clients never see each other's addresses.
    assert all(message["Cc"] is None and message["Bcc"] is None for message in sent)
    assert smtp.instances[0].started_tls and smtp.instances[0].quit_called


def test_broadcast_can_target_selected_clients(api, order, smtp):
    other = api.post("/clients/", json={
        "name": "Bruno", "email": "bruno@example.com",
        "phone_number": "+573001112233", "address": "123 Main St", "city": "Miami", "state": "FL", "country": "US", "zipcode": "33101", "password": "supersecret",
    }).json()

    response = api.post("/messages/broadcast", json={
        "subject": "Just you", "body": "Hello", "client_ids": [other["id"]],
    })

    assert response.json()["sent"] == 1
    assert [item["email"] for item in response.json()["results"]] == ["bruno@example.com"]


def test_broadcast_without_matching_clients_is_422(api, smtp):
    response = api.post("/messages/broadcast", json={
        "subject": "Hi", "body": "Hello", "client_ids": [4242],
    })
    assert response.status_code == 422


def test_one_refused_address_does_not_stop_the_batch(api, order, smtp):
    api.post("/clients/", json={
        "name": "Bruno", "email": "bruno@example.com",
        "phone_number": "+573001112233", "address": "123 Main St", "city": "Miami", "state": "FL", "country": "US", "zipcode": "33101", "password": "supersecret",
    })
    smtp.fail_for = {"ana@example.com"}

    body = api.post("/messages/broadcast", json={"subject": "Hi", "body": "Hello"}).json()

    assert (body["sent"], body["failed"]) == (1, 1)
    failed = next(item for item in body["results"] if item["status"] == "failed")
    assert failed["email"] == "ana@example.com"
    assert "550" in failed["detail"] or "refused" in failed["detail"].lower()


def test_unreachable_mail_server_is_503(api, order, smtp):
    smtp.connect_error = OSError("Connection refused")
    response = api.post("/messages/broadcast", json={"subject": "Hi", "body": "Hello"})
    assert response.status_code == 503
    assert "mail server" in response.json()["detail"].lower()


def test_emailing_an_invoice_attaches_the_pdf(api, order, smtp):
    response = api.post(f"/invoices/{order['order']['id']}/email")

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert response.json()["email"] == "ana@example.com"

    message = smtp.instances[0].sent[0]
    attachments = [part for part in message.walk() if part.get_filename()]
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "INV-00001.pdf"
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_payload(decode=True).startswith(b"%PDF")
    assert "103.50" in message.get_body(("plain",)).get_content()


def test_messages_routes_require_authentication(raw_api):
    assert raw_api.get("/messages/status").status_code == 401
    assert raw_api.post("/messages/broadcast", json={}).status_code == 401
    assert raw_api.get("/invoices/1").status_code == 401
    assert raw_api.get("/invoices/1/pdf").status_code == 401
    assert raw_api.post("/invoices/1/email").status_code == 401
