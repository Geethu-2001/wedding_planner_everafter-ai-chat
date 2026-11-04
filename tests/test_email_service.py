import pytest
from wedding_planner.services.email_service import send_wedding_pdf,allowed_recipients,EmailDeliveryError
from wedding_planner.models import EmailHistory
class FakeProvider:
    def __init__(self,fail=False):self.fail=fail
    def send(self,*args):
        if self.fail:raise RuntimeError("provider unavailable")
        return type("Result",(),{"provider":"fake","message_id":"ok"})()
def test_success_and_partner(session,couple,tmp_path):
    a,b,c,w=couple;p=tmp_path/"plan.pdf";p.write_bytes(b"%PDF")
    assert allowed_recipients(session,w.id,a.id)["Verified wedding partner"]==b.email
    h=send_wedding_pdf(session,wedding_id=w.id,user_id=a.id,recipient=a.email,pdf_path=p,pdf_version=2,provider=FakeProvider())
    assert h.status=="sent" and h.pdf_version==2
def test_invalid_recipient(session,couple,tmp_path):
    a,b,c,w=couple;p=tmp_path/"x.pdf";p.write_bytes(b"x")
    with pytest.raises(PermissionError):
        send_wedding_pdf(session,wedding_id=w.id,user_id=a.id,recipient=c.email,pdf_path=p,pdf_version=1,provider=FakeProvider())
def test_authorization_failure(session,couple,tmp_path):
    a,b,c,w=couple;p=tmp_path/"x.pdf";p.write_bytes(b"x")
    with pytest.raises(PermissionError):
        send_wedding_pdf(session,wedding_id=w.id,user_id=c.id,recipient=a.email,pdf_path=p,pdf_version=1,provider=FakeProvider())
def test_provider_error_logged(session,couple,tmp_path):
    a,b,c,w=couple;p=tmp_path/"x.pdf";p.write_bytes(b"x")
    with pytest.raises(EmailDeliveryError):
        send_wedding_pdf(session,wedding_id=w.id,user_id=a.id,recipient=a.email,pdf_path=p,pdf_version=1,provider=FakeProvider(True))
    row=session.query(EmailHistory).one()
    assert row.status=="failed" and "provider unavailable" in row.error_message
