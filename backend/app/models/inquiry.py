from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from backend.app.database.session import Base

class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String, nullable=False)  # "Job Seeker", "Client Company", "Supervisor Inquiry", "Other"
    message = Column(Text, nullable=False)
    status = Column(String, default="NEW", nullable=False)  # "NEW", "CONTACTED", "RESOLVED"
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

