from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class SupervisorProfile(Base):
    __tablename__ = "supervisor_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    area = Column(String, nullable=False)
    city = Column(String, nullable=False)
    is_approved = Column(Boolean, default=False)
    
    # Admin assigned deployment scope & GPS coordinates
    assigned_company = Column(String, nullable=True)     # e.g., "Tata Motors", "Amazon", "All"
    assigned_location = Column(String, nullable=True)    # e.g., "Chakan MIDC, Pune"
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    geofence_radius = Column(Integer, default=1000)      # meters
    
    # Live GPS tracking
    last_seen_lat = Column(String, nullable=True)
    last_seen_lng = Column(String, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_location_address = Column(String, nullable=True)
    
    # Termination tracking
    termination_reason = Column(Text, nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="supervisor_profile")
    deployments = relationship("Deployment", back_populates="supervisor")
