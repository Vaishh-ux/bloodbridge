from app.timeutil import utcnow
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class EmergencyLevel(str, enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    NORMAL = "Normal"


class RequestStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    SEARCHING = "SEARCHING"
    DONOR_FOUND = "DONOR_FOUND"
    DONOR_ACCEPTED = "DONOR_ACCEPTED"
    HOSPITAL_CONFIRMED = "HOSPITAL_CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


ACTIVE_STATUSES = (
    RequestStatus.REQUESTED,
    RequestStatus.SEARCHING,
    RequestStatus.DONOR_FOUND,
    RequestStatus.DONOR_ACCEPTED,
    RequestStatus.HOSPITAL_CONFIRMED,
)

URGENCY_ORDER = {
    EmergencyLevel.CRITICAL: 0,
    EmergencyLevel.HIGH: 1,
    EmergencyLevel.MEDIUM: 2,
    EmergencyLevel.NORMAL: 3,
}


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id = Column(Integer, primary_key=True, index=True)
    # The account that created the request (patient, hospital or admin) owns it.
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id", ondelete="SET NULL"), nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    patient_name = Column(String(150), nullable=True)  # private: never shown publicly
    hospital_name = Column(String(150), nullable=False)
    hospital_address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    blood_group = Column(String(5), nullable=False, index=True)
    units_required = Column(Integer, default=1, nullable=False)
    emergency_level = Column(Enum(EmergencyLevel, name="emergency_level"), default=EmergencyLevel.HIGH, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    required_date = Column(String(20), nullable=False)
    required_time = Column(String(20), nullable=False)
    status = Column(Enum(RequestStatus, name="request_status"), default=RequestStatus.REQUESTED, nullable=False, index=True)
    notes = Column(Text, nullable=True)  # private: shown only to owner, hospital and admin
    is_suspicious = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    created_by = relationship("User")
    patient = relationship("PatientProfile", back_populates="requests")
    hospital = relationship("Hospital", back_populates="requests")
    matches = relationship("DonorMatch", back_populates="request", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="request", cascade="all, delete-orphan")
    donations = relationship("Donation", back_populates="request")

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES
