from app.timeutil import utcnow
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class DonorProfile(Base):
    __tablename__ = "donor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    blood_group = Column(String(5), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(15), nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=True, index=True)
    # Location is optional: donors without coordinates are matched by city instead of distance.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    available = Column(Boolean, default=True, index=True, nullable=False)
    last_donation_date = Column(Date, nullable=True)
    # Donor's own confirmation that they meet the basic self-screening questions.
    screening_passed = Column(Boolean, default=False, nullable=False)
    total_donations = Column(Integer, default=0, nullable=False)
    successful_donations = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="donor_profile")
    matches = relationship("DonorMatch", back_populates="donor", cascade="all, delete-orphan")
    donations = relationship("Donation", back_populates="donor", cascade="all, delete-orphan")
