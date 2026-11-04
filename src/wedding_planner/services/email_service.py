from pathlib import Path
from wedding_planner.config import settings
from wedding_planner.integrations.email import get_email_provider
from wedding_planner.models import EmailHistory,User,WeddingMember
from wedding_planner.repositories import require_membership
from wedding_planner.security import normalize_email
class EmailDeliveryError(RuntimeError): pass
def allowed_recipients(session,wedding_id,user_id):
    require_membership(session,wedding_id,user_id)
    user=session.get(User,user_id); result={"My account email":user.email}
    members=session.query(WeddingMember).filter(WeddingMember.wedding_id==wedding_id,WeddingMember.user_id!=user_id).all()
    for m in members:
        partner=session.get(User,m.user_id)
        if partner and partner.email_verified: result["Verified wedding partner"]=partner.email
    return result
def send_wedding_pdf(session,*,wedding_id,user_id,recipient,pdf_path,pdf_version,provider=None):
    require_membership(session,wedding_id,user_id)
    recipient=normalize_email(recipient)
    if recipient not in set(allowed_recipients(session,wedding_id,user_id).values()):
        raise PermissionError("Recipient must be your registered email or a verified wedding partner.")
    path=Path(pdf_path)
    if not path.is_file(): raise FileNotFoundError("Generated PDF not found.")
    history=EmailHistory(wedding_id=wedding_id,sender_user_id=user_id,recipient=recipient,
        pdf_version=pdf_version,status="pending",provider=settings.email_provider)
    session.add(history); session.commit()
    try:
        if path.stat().st_size>settings.email_max_attachment_mb*1024*1024:
            raise EmailDeliveryError(f"PDF exceeds the configured {settings.email_max_attachment_mb} MB attachment limit.")
        result=(provider or get_email_provider()).send(recipient,"Your EverAfter AI wedding plan",
            "Attached is the latest version of your wedding plan PDF.",path)
        history.status="sent"; history.provider=result.provider; session.commit(); return history
    except Exception as exc:
        history.status="failed"; history.error_message=str(exc)[:2000]; session.commit()
        if isinstance(exc,EmailDeliveryError): raise
        raise EmailDeliveryError(str(exc)) from exc
