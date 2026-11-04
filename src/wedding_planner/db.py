from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from wedding_planner.config import settings
class Base(DeclarativeBase): pass
kwargs = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"): kwargs = {"connect_args": {"check_same_thread": False}}
engine = create_engine(settings.database_url, **kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
