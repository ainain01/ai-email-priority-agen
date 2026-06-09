"""
Database setup using SQLite via SQLAlchemy.
Stores processed email IDs to prevent duplicates.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./email_agent.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    id = Column(String, primary_key=True, index=True)
    sender = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body_preview = Column(Text, nullable=True)
    is_important = Column(Boolean, default=False)
    priority = Column(String, nullable=True)       # HIGH / MEDIUM / LOW
    category = Column(String, nullable=True)       # PAYMENT_ISSUE, SERVER_DOWN, etc.
    reason = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    return SessionLocal()
