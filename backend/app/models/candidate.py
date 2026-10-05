from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    dob = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    current_address = Column(String, nullable=True)
    permanent_address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pin_code = Column(String, nullable=True)
    qualification = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    preferred_job = Column(String, nullable=True)
    preferred_location = Column(String, nullable=True)
    expected_salary = Column(String, nullable=True)
    preferred_shift = Column(String, nullable=True)
    source = Column(String, nullable=True)
    profile_photo = Column(String, nullable=True)
    
    user = relationship("User", back_populates="candidate_profile")
    applications = relationship("JobApplication", back_populates="candidate")
