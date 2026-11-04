from sqlalchemy.orm import Session
from wedding_planner.models import User
from wedding_planner.security import hash_password,normalize_email,verify_password
def register_user(session: Session,full_name: str,email: str,password: str,role: str="Partner"):
    email=normalize_email(email)
    if len(password)<10: raise ValueError("Password must contain at least 10 characters.")
    if session.query(User).filter_by(email=email).first(): raise ValueError("An account with this email already exists.")
    user=User(full_name=full_name.strip(),email=email,password_hash=hash_password(password),account_role=role)
    session.add(user); session.commit(); session.refresh(user); return user
def authenticate_user(session: Session,email: str,password: str):
    user=session.query(User).filter_by(email=normalize_email(email),is_active=True).first()
    return user if user and verify_password(password,user.password_hash) else None
