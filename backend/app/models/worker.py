from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Time, Numeric, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class WorkerProfile(Base):
    __tablename__ = "worker_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    deployment_id = Column(Integer, ForeignKey("deployments.id"), unique=True)
    
    # Termination info
    termination_reason = Column(Text, nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="worker_profile")
    deployment = relationship("Deployment", back_populates="worker_profile")
    attendances = relationship("Attendance", back_populates="worker")
    payrolls = relationship("Payroll", back_populates="worker")
    complaints = relationship("Complaint", back_populates="worker")

class Attendance(Base):
    __tablename__ = "attendances"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"))
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False) # PRESENT, ABSENT, HALF_DAY, LEAVE
    check_in = Column(Time, nullable=True)
    check_out = Column(Time, nullable=True)
    
    # GPS Verification details
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    location_address = Column(String, nullable=True)
    is_gps_verified = Column(Boolean, default=False)
    
    worker = relationship("WorkerProfile", back_populates="attendances")

class Payroll(Base):
    __tablename__ = "payrolls"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"))
    month = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    basic_salary = Column(Numeric(10, 2), nullable=False)
    deductions = Column(Numeric(10, 2), default=0)
    net_salary = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="PENDING")
    
    worker = relationship("WorkerProfile", back_populates="payrolls")

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="OPEN") # OPEN, IN_PROGRESS, RESOLVED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    worker = relationship("WorkerProfile", back_populates="complaints")
