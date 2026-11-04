import bcrypt
from email_validator import validate_email, EmailNotValidError
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()
def verify_password(password: str,password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(),password_hash.encode())
def normalize_email(email: str) -> str:
    try: return validate_email(email,check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc: raise ValueError("Please enter a valid email address.") from exc
