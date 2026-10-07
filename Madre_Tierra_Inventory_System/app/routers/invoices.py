from fastapi import APIRouter, Response

from app.routers.dependencies import PositiveId, SessionDep, service_errors
from app.schema.invoice import InvoiceRead
from app.schema.message import RecipientResult
from app.service.invoice_service import build_invoice, render_invoice_pdf
from app.service.message_service import email_invoice_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/{order_id}", response_model=InvoiceRead)
def get_invoice(order_id: PositiveId, session: SessionDep):
    """Invoice data for an order, for on-screen preview."""
    with service_errors():
        return build_invoice(session, order_id)


@router.get(
    "/{order_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_invoice_pdf(order_id: PositiveId, session: SessionDep):
    with service_errors():
        invoice = build_invoice(session, order_id)
    pdf = render_invoice_pdf(invoice)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{invoice.invoice_number}.pdf"'
            ),
            "Content-Length": str(len(pdf)),
        },
    )


@router.post("/{order_id}/email", response_model=RecipientResult)
def email_invoice(order_id: PositiveId, session: SessionDep):
    """Send the order's invoice to its client as a PDF attachment."""
    with service_errors():
        return email_invoice_service(session, order_id)
