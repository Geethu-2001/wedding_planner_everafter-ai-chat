import hashlib,secrets
from datetime import datetime,timedelta
from wedding_planner.models import Wedding,WeddingMember,Invitation
from wedding_planner.repositories import require_membership
def create_wedding(session,owner,**fields):
    wedding=Wedding(created_by=owner.id,**fields); session.add(wedding); session.flush()
    session.add(WeddingMember(wedding_id=wedding.id,user_id=owner.id,access_role="owner"))
    session.commit(); session.refresh(wedding); return wedding
def invite_partner(session,wedding_id,actor_id,email):
    require_membership(session,wedding_id,actor_id)
    token=secrets.token_urlsafe(32)
    row=Invitation(wedding_id=wedding_id,invited_email=email.lower().strip(),
        token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=datetime.utcnow()+timedelta(days=7))
    session.add(row); session.commit(); return row,token
def accept_invitation(session,token,user):
    row=session.query(Invitation).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not row or row.status!="pending" or row.expires_at<datetime.utcnow(): raise ValueError("Invitation invalid or expired.")
    if row.invited_email!=user.email: raise PermissionError("Invitation email does not match.")
    session.add(WeddingMember(wedding_id=row.wedding_id,user_id=user.id,access_role="editor"))
    row.status="accepted"; user.email_verified=True; session.commit()
