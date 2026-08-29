"""
enquiry.py — Landing page Early Access enquiry router with Background Email Alerts
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, EmailStr
from app.db.supabase_client import get_supabase_async
from app.config import get_settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Enquiry"])


class EnquiryCreate(BaseModel):
    name: str
    firm: str | None = None
    city: str | None = None
    email: str  # ya EmailStr (agar email-validator installed ho)
    phone: str | None = None
    clients: str | None = None
    message: str | None = None


def send_email_alert(lead: dict):
    """
    Sends an instant notification when a CA requests early access.
    Non-blocking execution via FastAPI BackgroundTasks.
    """
    settings = get_settings()
    
    # Configure in your .env or fallback values
    smtp_host = getattr(settings, "smtp_host", "smtp.gmail.com")
    smtp_port = getattr(settings, "smtp_port", 465)
    smtp_user = getattr(settings, "smtp_user", "hello@auditai.in")
    smtp_password = getattr(settings, "smtp_password", "")
    alert_receiver = getattr(settings, "alert_receiver", "hello@auditai.in")

    if not smtp_password:
        logger.info(f"Skipping email alert (no SMTP password configured). Lead logged: {lead.get('email')}")
        return

    subject = f"🚨 New CA Early Access Request: {lead.get('name')} ({lead.get('city') or 'No City'})"
    body = f"""
New CA Early Access Lead Received!
-----------------------------------
Name:       {lead.get('name')}
Firm:       {lead.get('firm') or 'N/A'}
City:       {lead.get('city') or 'N/A'}
Email:      {lead.get('email')}
Phone:      {lead.get('phone') or 'N/A'}
Clients:    {lead.get('clients') or 'N/A'}

Pain Point / Message:
{lead.get('message') or 'No message provided'}
-----------------------------------
Action: Reach out within 24 hours to schedule a discovery call.
    """

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = alert_receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info(f"Email alert dispatched for {lead.get('email')}")
    except Exception as e:
        logger.error(f"Failed to dispatch email alert: {e}", exc_info=True)


@router.post("/enquiry", status_code=status.HTTP_201_CREATED)
async def submit_enquiry(payload: EnquiryCreate, background_tasks: BackgroundTasks):
    try:
        supabase = await get_supabase_async()
        data = payload.model_dump()

        # 1. Save directly into Supabase table
        supabase.table("enquiries").insert(data).execute()

        # 2. Trigger asynchronous email notification
        background_tasks.add_task(send_email_alert, data)

        logger.info(f"New Early Access enquiry saved: {payload.email} ({payload.name})")
        return {"status": "success", "message": "Enquiry registered successfully"}
    except Exception as e:
        logger.error(f"Failed to save enquiry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit enquiry"
        )