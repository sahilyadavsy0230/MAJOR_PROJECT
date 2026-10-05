import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class DocumentStatus(str, enum.Enum):
    PENDING  = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class Document(Base):
    __tablename__ = "documents"
    id               = Column(Integer, primary_key=True, index=True)
    # application_id is nullable: docs uploaded at registration have no app yet
    application_id   = Column(Integer, ForeignKey("job_applications.id"), nullable=True)
    # uploaded_by_user_id: links docs to the candidate user regardless of application
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    document_type    = Column(String, nullable=False)   # e.g. 'Aadhaar Card', '10th Marksheet'
    file_path        = Column(String, nullable=False)
    status           = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    uploaded_at      = Column(DateTime(timezone=True), server_default=func.now())

    application  = relationship("JobApplication", back_populates="documents")
    uploader     = relationship("User", foreign_keys=[uploaded_by_user_id])
