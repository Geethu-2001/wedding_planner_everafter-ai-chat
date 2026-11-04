from dataclasses import dataclass
from pathlib import Path
from email.message import EmailMessage
import base64,smtplib
import resend
from wedding_planner.config import settings
@dataclass
class DeliveryResult:
    provider: str
    message_id: str|None=None
class EmailProviderError(RuntimeError): pass
class ResendProvider:
    def send(self,recipient,subject,body,attachment: Path):
        if not settings.resend_api_key: raise EmailProviderError("RESEND_API_KEY is not configured.")
        resend.api_key=settings.resend_api_key
        try:
            response=resend.Emails.send({"from":settings.email_from,"to":[recipient],"subject":subject,
                "text":body,"attachments":[{"filename":attachment.name,
                "content":base64.b64encode(attachment.read_bytes()).decode("ascii")}]})
            return DeliveryResult("resend",str(response.get("id")) if isinstance(response,dict) else None)
        except Exception as exc: raise EmailProviderError(f"Resend delivery failed: {exc}") from exc
class SMTPProvider:
    def send(self,recipient,subject,body,attachment: Path):
        if not settings.smtp_host or not settings.email_from: raise EmailProviderError("SMTP_HOST and EMAIL_FROM required.")
        msg=EmailMessage(); msg["From"]=settings.email_from; msg["To"]=recipient; msg["Subject"]=subject; msg.set_content(body)
        msg.add_attachment(attachment.read_bytes(),maintype="application",subtype="pdf",filename=attachment.name)
        try:
            with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=20) as server:
                if settings.smtp_use_tls: server.starttls()
                if settings.smtp_username: server.login(settings.smtp_username,settings.smtp_password)
                server.send_message(msg)
            return DeliveryResult("smtp")
        except Exception as exc: raise EmailProviderError(f"SMTP delivery failed: {exc}") from exc
def get_email_provider():
    if settings.email_provider.lower()=="resend": return ResendProvider()
    if settings.email_provider.lower()=="smtp": return SMTPProvider()
    raise EmailProviderError("EMAIL_PROVIDER must be resend or smtp.")
