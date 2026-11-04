from datetime import datetime, date
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from wedding_planner.db import Base
class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    full_name: Mapped[str]=mapped_column(String(160))
    email: Mapped[str]=mapped_column(String(320),unique=True,index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    account_role: Mapped[str]=mapped_column(String(30),default="Partner")
    is_active: Mapped[bool]=mapped_column(Boolean,default=True)
    email_verified: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Wedding(Base):
    __tablename__="weddings"
    id: Mapped[int]=mapped_column(primary_key=True)
    created_by: Mapped[int]=mapped_column(ForeignKey("users.id"))
    bride_name: Mapped[str]=mapped_column(String(160),default="")
    groom_name: Mapped[str]=mapped_column(String(160),default="")
    wedding_date: Mapped[date|None]=mapped_column(Date,nullable=True)
    country: Mapped[str]=mapped_column(String(100),default="India")
    state: Mapped[str]=mapped_column(String(100),default="")
    district: Mapped[str]=mapped_column(String(100),default="")
    city: Mapped[str]=mapped_column(String(100),default="")
    guest_count: Mapped[int]=mapped_column(Integer,default=0)
    wedding_style: Mapped[str]=mapped_column(String(50),default="Traditional")
    wedding_type: Mapped[str]=mapped_column(String(50),default="")
    total_budget: Mapped[float]=mapped_column(Numeric(14,2),default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class WeddingMember(Base):
    __tablename__="wedding_members"
    __table_args__=(UniqueConstraint("wedding_id","user_id"),)
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"))
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"))
    access_role: Mapped[str]=mapped_column(String(30),default="editor")
    joined_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Invitation(Base):
    __tablename__="invitations"
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"))
    invited_email: Mapped[str]=mapped_column(String(320))
    token_hash: Mapped[str]=mapped_column(String(64),unique=True)
    status: Mapped[str]=mapped_column(String(20),default="pending")
    expires_at: Mapped[datetime]=mapped_column(DateTime)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class WeddingService(Base):
    __tablename__="wedding_services"
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"),index=True)
    category: Mapped[str]=mapped_column(String(120))
    requirements: Mapped[str]=mapped_column(Text,default="")
    status: Mapped[str]=mapped_column(String(30),default="needed")
    notes: Mapped[str]=mapped_column(Text,default="")
class Vendor(Base):
    __tablename__="vendors"
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"),index=True)
    category: Mapped[str]=mapped_column(String(120),index=True)
    name: Mapped[str]=mapped_column(String(200))
    location: Mapped[str]=mapped_column(String(200),default="")
    description: Mapped[str]=mapped_column(Text,default="")
    source_url: Mapped[str]=mapped_column(Text,default="")
    research_status: Mapped[str]=mapped_column(String(30),default="lead")
    price_text: Mapped[str]=mapped_column(String(240),default="Not published")
    package_details: Mapped[str]=mapped_column(Text,default="")
    contact_details: Mapped[str]=mapped_column(Text,default="")
    result_summary: Mapped[str]=mapped_column(Text,default="")
    quoted_amount: Mapped[float|None]=mapped_column(Numeric(14,2),nullable=True)
    selection_status: Mapped[str]=mapped_column(String(30),default="not_selected")
    notes: Mapped[str]=mapped_column(Text,default="")
    researched_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Expense(Base):
    __tablename__="expenses"
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"),index=True)
    category: Mapped[str]=mapped_column(String(120))
    description: Mapped[str]=mapped_column(String(300))
    amount: Mapped[float]=mapped_column(Numeric(14,2))
    expense_type: Mapped[str]=mapped_column(String(30),default="planned")
    payment_status: Mapped[str]=mapped_column(String(30),default="unpaid")
class WeddingTask(Base):
    __tablename__="wedding_tasks"
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"),index=True)
    title: Mapped[str]=mapped_column(String(200))
    due_date: Mapped[date|None]=mapped_column(Date,nullable=True)
    priority: Mapped[str]=mapped_column(String(20),default="medium")
    status: Mapped[str]=mapped_column(String(20),default="pending")
class WeddingDocument(Base):
    __tablename__="wedding_documents"
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"),index=True)
    file_path: Mapped[str]=mapped_column(Text)
    version: Mapped[int]=mapped_column(Integer)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class EmailHistory(Base):
    __tablename__="email_history"
    id: Mapped[int]=mapped_column(primary_key=True)
    wedding_id: Mapped[int]=mapped_column(ForeignKey("weddings.id",ondelete="CASCADE"),index=True)
    sender_user_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    recipient: Mapped[str]=mapped_column(String(320))
    pdf_version: Mapped[int]=mapped_column(Integer)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    status: Mapped[str]=mapped_column(String(20),default="pending")
    provider: Mapped[str]=mapped_column(String(30))
    error_message: Mapped[str]=mapped_column(Text,default="")
