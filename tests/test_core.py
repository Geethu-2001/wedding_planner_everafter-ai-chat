from decimal import Decimal
from wedding_planner.services.budget_service import suggest_budget_allocation
from wedding_planner.repositories import require_membership,AuthorizationError
from wedding_planner.services.auth_service import register_user,authenticate_user
import pytest
def test_budget_allocations():
    assert sum(suggest_budget_allocation(Decimal("100000"))) == Decimal("100000.00")
def test_membership(session,couple):
    a,b,c,w=couple
    assert require_membership(session,w.id,a.id)
    with pytest.raises(AuthorizationError):require_membership(session,w.id,c.id)
def test_auth(session):
    u=register_user(session,"Test Person","test@example.com","StrongPassword123")
    assert u.password_hash!="StrongPassword123"
    assert authenticate_user(session,u.email,"StrongPassword123")
    assert authenticate_user(session,u.email,"bad") is None
