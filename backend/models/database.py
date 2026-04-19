"""
Database models for workflow management.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Use absolute path based on project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "workflows.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Workflow(Base):
    """Workflow model."""
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    folder = Column(String(255), nullable=False, default="")  # Folder path, e.g. "reports/daily"
    config = Column(JSON, nullable=False)  # Full workflow YAML as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    executions = relationship("Execution", back_populates="workflow")


class Execution(Base):
    """Workflow execution record."""
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    status = Column(String(50), nullable=False)  # running, success, failed, cancelled
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    result = Column(JSON, nullable=True)  # execution result details
    logs = Column(Text, nullable=True)  # execution logs

    # Relationship
    workflow = relationship("Workflow", back_populates="executions")


class Folder(Base):
    """Folder model for organizing workflows."""
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(255), nullable=False, unique=True)  # Folder path e.g. "reports/daily"
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
