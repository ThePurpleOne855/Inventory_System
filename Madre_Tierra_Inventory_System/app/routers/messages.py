from fastapi import APIRouter

from app.routers.dependencies import SessionDep, service_errors
from app.schema.message import BroadcastRequest, BroadcastResult, MailStatus
from app.service.message_service import mail_status, send_broadcast_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/status", response_model=MailStatus)
def get_mail_status():
    """Tell the UI whether SMTP is configured before it offers to send."""
    return mail_status()


@router.post("/broadcast", response_model=BroadcastResult)
def send_broadcast(request: BroadcastRequest, session: SessionDep):
    with service_errors():
        return send_broadcast_service(session, request)
