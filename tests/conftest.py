import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from wedding_planner.db import Base
from wedding_planner.models import User,Wedding,WeddingMember
from wedding_planner.security import hash_password
@pytest.fixture
def session():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db=sessionmaker(bind=engine,expire_on_commit=False)()
    yield db
    db.close()
@pytest.fixture
def couple(session):
    a=User(full_name="Aarav",email="aarav@example.com",password_hash=hash_password("StrongPass123!"),email_verified=True)
    b=User(full_name="Ananya",email="ananya@example.com",password_hash=hash_password("StrongPass123!"),email_verified=True)
    c=User(full_name="Other",email="other@example.com",password_hash=hash_password("StrongPass123!"))
    session.add_all([a,b,c]);session.flush()
    w=Wedding(created_by=a.id,bride_name="Ananya",groom_name="Aarav",city="Kochi",total_budget=1500000)
    session.add(w);session.flush()
    session.add_all([WeddingMember(wedding_id=w.id,user_id=a.id,access_role="owner"),WeddingMember(wedding_id=w.id,user_id=b.id)])
    session.commit();return a,b,c,w
