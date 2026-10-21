from app.timeutil import utcnow
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class FacilityType(str, enum.Enum):
    HOSPITAL = "HOSPITAL"
    BLOOD_BANK = "BLOOD_BANK"


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    facility_type = Column(Enum(FacilityType, name="facility_type"), default=FacilityType.HOSPITAL, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    # Only an administrator can mark a facility as verified.
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="hospital_profile")
    inventory = relationship("BloodInventory", back_populates="hospital", cascade="all, delete-orphan")
    requests = relationship("BloodRequest", back_populates="hospital")
