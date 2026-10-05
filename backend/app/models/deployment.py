from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Deployment(Base):
    __tablename__ = "deployments"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("job_applications.id"), unique=True)
    worker_id_str = Column(String, unique=True, index=True, nullable=False)
    company = Column(String, nullable=False)
    job_role = Column(String, nullable=False)
    supervisor_id = Column(Integer, ForeignKey("supervisor_profiles.id"), nullable=True)
    joining_date = Column(Date, nullable=False)
    shift = Column(String, nullable=False)
    area = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Termination tracking
    termination_reason = Column(Text, nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    
    application = relationship("JobApplication", back_populates="deployment")
    supervisor = relationship("SupervisorProfile", back_populates="deployments")
    worker_profile = relationship("WorkerProfile", back_populates="deployment", uselist=False)
