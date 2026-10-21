from app.timeutil import utcnow
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("donor_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(Integer, ForeignKey("blood_requests.id", ondelete="SET NULL"), nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True)
    match_id = Column(Integer, ForeignKey("donor_matches.id", ondelete="SET NULL"), nullable=True)
    confirmed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    blood_group = Column(String(5), nullable=False)
    units = Column(Integer, default=1, nullable=False)
    donation_date = Column(Date, default=date.today, nullable=False)
    status = Column(String(20), default="COMPLETED", nullable=False)
    certificate_number = Column(String(50), unique=True, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    donor = relationship("DonorProfile", back_populates="donations")
    request = relationship("BloodRequest", back_populates="donations")
    hospital = relationship("Hospital")
