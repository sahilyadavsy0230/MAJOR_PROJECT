import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Date, Time
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class InterviewStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("job_applications.id"), unique=True)
    hr_name = Column(String, nullable=False)
    client_name = Column(String, nullable=False)
    interview_date = Column(Date, nullable=False)
    interview_time = Column(Time, nullable=False)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.SCHEDULED)
    
    application = relationship("JobApplication", back_populates="interview")
