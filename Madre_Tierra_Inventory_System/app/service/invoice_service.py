"""Turn a stored order into invoice data, and that data into a PDF."""
from decimal import Decimal
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlmodel import Session

from app.core.config import settings
from app.crud.product import get_product
from app.schema.client import ClientRead
from app.schema.invoice import InvoiceCompany, InvoiceLine, InvoiceRead
from app.service.client_service import retrieve_client_by_id_service
from app.service.order_service import (
    get_order_products_for_order_service,
    retrieve_order_by_id_service,
)

INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
RULE = colors.HexColor("#d1d5db")
BAND = colors.HexColor("#f3f4f6")


def build_invoice(session: Session, order_id: int) -> InvoiceRead:
    """Collect an order, its client, and its line items into invoice data."""
    order = retrieve_order_by_id_service(session, order_id)
    client = retrieve_client_by_id_service(session, order.client_id)
    items = get_order_products_for_order_service(session, order_id)

    lines: list[InvoiceLine] = []
    subtotal = Decimal("0")
    for item in items:
        product = get_product(session, item.product_id)
        # A product can be renamed or removed after the order was placed; the
        # order's own unit_price and quantity stay authoritative either way.
        name = product.name if product is not None else f"Product #{item.product_id}"
        line_total = item.unit_price * item.quantity
        subtotal += line_total
        lines.append(
            InvoiceLine(
                product_id=item.product_id,
                product_name=name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
            )
        )

    return InvoiceRead(
        invoice_number=f"INV-{order_id:05d}",
        order_id=order_id,
        created_at=order.created_at,
        client=ClientRead.model_validate(client, from_attributes=True),
        lines=lines,
        subtotal=subtotal,
        total=Decimal(str(order.total)),
        currency=settings.currency,
        company=InvoiceCompany(
            name=settings.company_name,
            address=settings.company_address,
            email=settings.company_email,
            phone=settings.company_phone,
        ),
    )


def display_phone(value: object) -> str:
    """pydantic's PhoneNumber renders as "tel:+1-555-..."; drop the scheme."""
    text = str(value or "")
    return text.removeprefix("tel:")


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency}{amount:,.2f}"


def render_invoice_pdf(invoice: InvoiceRead) -> bytes:
    """Render invoice data as a single-page A4 PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{invoice.invoice_number} — {invoice.company.name}",
        author=invoice.company.name,
    )

    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "title", parent=base["Title"], fontSize=22, alignment=0, textColor=INK,
        spaceAfter=2,
    )
    heading = ParagraphStyle(
        "heading", parent=base["Normal"], fontSize=8, textColor=MUTED,
        fontName="Helvetica-Bold", spaceAfter=3, leading=11,
    )
    body = ParagraphStyle(
        "body", parent=base["Normal"], fontSize=10, textColor=INK, leading=14
    )
    right = ParagraphStyle("right", parent=body, alignment=TA_RIGHT)
    cell = ParagraphStyle("cell", parent=base["Normal"], fontSize=9.5, leading=12)

    company_block = [f"<b>{invoice.company.name}</b>"]
    company_block += [
        value
        for value in (
            invoice.company.address,
            invoice.company.email,
            display_phone(invoice.company.phone),
        )
        if value
    ]

    client = invoice.client
    client_name = " ".join(filter(None, (client.name, client.last_name)))
    client_block = [
        f"<b>{client_name}</b>",
        str(client.email),
        display_phone(client.phone_number),
    ]
    for part in (client.address, " ".join(filter(None, (client.city, client.state, client.zipcode))), client.country):
        if part:
            client_block.append(escape(part).replace("\n", "<br/>"))

    story = [
        Table(
            [[
                Paragraph("INVOICE", title),
                Paragraph("<br/>".join(company_block), right),
            ]],
            colWidths=[doc.width * 0.5, doc.width * 0.5],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]),
        ),
        Spacer(1, 10 * mm),
        Table(
            [[
                Paragraph("BILL TO", heading),
                Paragraph("INVOICE NUMBER", heading),
                Paragraph("ORDER DATE", heading),
            ], [
                Paragraph("<br/>".join(client_block), body),
                Paragraph(invoice.invoice_number, body),
                Paragraph(invoice.created_at.strftime("%d %b %Y"), body),
            ]],
            colWidths=[doc.width * 0.5, doc.width * 0.25, doc.width * 0.25],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ]),
        ),
        Spacer(1, 10 * mm),
    ]

    rows = [[
        Paragraph("<b>Item</b>", cell),
        Paragraph("<b>Qty</b>", cell),
        Paragraph("<b>Unit price</b>", cell),
        Paragraph("<b>Amount</b>", cell),
    ]]
    for line in invoice.lines:
        rows.append([
            Paragraph(line.product_name, cell),
            Paragraph(str(line.quantity), cell),
            Paragraph(_money(line.unit_price, invoice.currency), cell),
            Paragraph(_money(line.line_total, invoice.currency), cell),
        ])
    if not invoice.lines:
        rows.append([Paragraph("<i>This order has no line items.</i>", cell), "", "", ""])

    widths = [doc.width * 0.46, doc.width * 0.12, doc.width * 0.21, doc.width * 0.21]
    items_table = Table(rows, colWidths=widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, RULE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    totals = [["", Paragraph("Subtotal", body),
               Paragraph(_money(invoice.subtotal, invoice.currency), right)]]
    if invoice.subtotal != invoice.total:
        totals.append(["", Paragraph("Adjustments", body), Paragraph(
            _money(invoice.total - invoice.subtotal, invoice.currency), right)])
    totals.append(["", Paragraph("<b>Total due</b>", body), Paragraph(
        f"<b>{_money(invoice.total, invoice.currency)}</b>", right)])

    totals_table = Table(
        totals,
        colWidths=[doc.width * 0.54, doc.width * 0.25, doc.width * 0.21],
    )
    totals_table.setStyle(TableStyle([
        ("LINEABOVE", (1, -1), (-1, -1), 0.75, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        f"Thank you for your business. Questions about this invoice? "
        f"Contact {invoice.company.email or invoice.company.name}.",
        ParagraphStyle("footer", parent=body, fontSize=8.5, textColor=MUTED),
    ))

    doc.build(story)
    return buffer.getvalue()
