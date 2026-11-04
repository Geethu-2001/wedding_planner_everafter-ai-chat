from sqlalchemy.orm import Session
from wedding_planner.models import WeddingMember
class AuthorizationError(PermissionError): pass
def require_membership(session: Session,wedding_id: int,user_id: int):
    member=session.query(WeddingMember).filter_by(wedding_id=wedding_id,user_id=user_id).first()
    if member is None: raise AuthorizationError("You are not a member of this wedding project.")
    return member
