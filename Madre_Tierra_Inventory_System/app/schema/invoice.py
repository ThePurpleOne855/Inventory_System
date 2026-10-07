from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.schema.client import ClientRead


class InvoiceLine(SQLModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class InvoiceCompany(SQLModel):
    name: str
    address: str = ""
    email: str = ""
    phone: str = ""


class InvoiceRead(SQLModel):
    """Everything needed to render an order as an invoice, on screen or as a PDF."""

    invoice_number: str
    order_id: int
    created_at: datetime
    client: ClientRead
    lines: list[InvoiceLine]
    subtotal: Decimal
    total: Decimal
    currency: str
    company: InvoiceCompany
