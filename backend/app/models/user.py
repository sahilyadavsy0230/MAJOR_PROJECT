import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CANDIDATE = "CANDIDATE"
    SUPERVISOR = "SUPERVISOR"
    WORKER = "WORKER"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CANDIDATE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    candidate_profile = relationship("CandidateProfile", back_populates="user", uselist=False)
    supervisor_profile = relationship("SupervisorProfile", back_populates="user", uselist=False)
    worker_profile = relationship("WorkerProfile", back_populates="user", uselist=False)
