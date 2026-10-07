"""Send email to clients over SMTP: broadcasts, and single invoices."""
import smtplib
from collections.abc import Iterator
from contextlib import contextmanager
from email.message import EmailMessage

from sqlmodel import Session, select

from app.core.config import settings
from app.models.client import Client
from app.schema.message import (
    BroadcastRequest,
    BroadcastResult,
    MailStatus,
    RecipientResult,
)
from app.service.client_service import retrieve_client_by_id_service
from app.service.invoice_service import build_invoice, render_invoice_pdf
from app.service.message_exceptions import (
    EmailNotConfiguredError,
    MailServerError,
    NoRecipientsError,
)


def mail_status() -> MailStatus:
    return MailStatus(
        configured=settings.email_configured,
        host=settings.smtp_host,
        sender=settings.mail_from,
    )


@contextmanager
def _smtp_connection() -> Iterator[smtplib.SMTP]:
    """One connection reused for every recipient in a broadcast."""
    if not settings.email_configured:
        raise EmailNotConfiguredError()
    try:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailServerError(str(exc)) from exc
    try:
        server.ehlo()
        if settings.smtp_starttls:
            server.starttls()
            server.ehlo()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        yield server
    except smtplib.SMTPException as exc:
        raise MailServerError(str(exc)) from exc
    finally:
        try:
            server.quit()
        except smtplib.SMTPException:
            server.close()


def _full_name(client: Client) -> str:
    return " ".join(filter(None, (client.name, client.last_name)))


def personalize(template: str, client: Client) -> str:
    """Fill {name}, {last_name} and {full_name} placeholders for one client.

    Unknown braces are left as-is rather than raising, so a stray "{" in a
    message body can never fail a send.
    """
    for token, value in (
        ("{name}", client.name or ""),
        ("{last_name}", client.last_name or ""),
        ("{full_name}", _full_name(client)),
    ):
        template = template.replace(token, value)
    return template


def _select_clients(session: Session, client_ids: list[int] | None) -> list[Client]:
    if client_ids:
        unique_ids = list(dict.fromkeys(client_ids))
        statement = select(Client).where(Client.id.in_(unique_ids))  # pyright: ignore[reportAttributeAccessIssue]
        found = {client.id: client for client in session.exec(statement)}
        # Ids that no longer exist are simply dropped; the caller sees the
        # shorter result list in the per-recipient report.
        return [found[cid] for cid in unique_ids if cid in found]
    return list(session.exec(select(Client)))


def send_broadcast_service(
    session: Session, request: BroadcastRequest
) -> BroadcastResult:
    """Email every selected client separately, and report per-recipient outcomes."""
    # Check configuration before the recipient list: "email is switched off" is
    # more actionable than "nobody matched" when neither is set up yet.
    if not settings.email_configured:
        raise EmailNotConfiguredError()

    recipients = _select_clients(session, request.client_ids)
    if not recipients:
        raise NoRecipientsError()

    results: list[RecipientResult] = []
    with _smtp_connection() as server:
        for client in recipients:
            message = EmailMessage()
            message["Subject"] = personalize(request.subject, client)
            message["From"] = settings.mail_from
            message["To"] = str(client.email)
            message.set_content(personalize(request.body, client))
            try:
                server.send_message(message)
                status, detail = "sent", ""
            except smtplib.SMTPException as exc:
                status, detail = "failed", str(exc)
            results.append(
                RecipientResult(
                    client_id=client.id or 0,
                    name=_full_name(client),
                    email=str(client.email),
                    status=status,
                    detail=detail,
                )
            )

    sent = sum(1 for result in results if result.status == "sent")
    return BroadcastResult(sent=sent, failed=len(results) - sent, results=results)


def email_invoice_service(session: Session, order_id: int) -> RecipientResult:
    """Email one order's invoice to its client as a PDF attachment."""
    invoice = build_invoice(session, order_id)
    client = retrieve_client_by_id_service(session, invoice.client.id)
    pdf = render_invoice_pdf(invoice)

    message = EmailMessage()
    message["Subject"] = f"{invoice.company.name} — invoice {invoice.invoice_number}"
    message["From"] = settings.mail_from
    message["To"] = str(client.email)
    message.set_content(
        f"Hello {_full_name(client)},\n\n"
        f"Your invoice {invoice.invoice_number} for order #{invoice.order_id} "
        f"is attached, totalling {invoice.currency}{invoice.total:,.2f}.\n\n"
        f"Thank you,\n{invoice.company.name}"
    )
    message.add_attachment(
        pdf,
        maintype="application",
        subtype="pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )

    with _smtp_connection() as server:
        try:
            server.send_message(message)
            status, detail = "sent", ""
        except smtplib.SMTPException as exc:
            status, detail = "failed", str(exc)

    return RecipientResult(
        client_id=client.id or 0,
        name=_full_name(client),
        email=str(client.email),
        status=status,
        detail=detail,
    )
