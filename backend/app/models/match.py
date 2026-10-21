from app.timeutil import utcnow
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class MatchStatus(str, enum.Enum):
    PENDING = "PENDING"        # donor notified, awaiting response
    ACCEPTED = "ACCEPTED"      # donor agreed to donate
    REJECTED = "REJECTED"      # donor declined
    CONFIRMED = "CONFIRMED"    # hospital confirmed the donation
    CLOSED = "CLOSED"          # request completed/cancelled before the donor responded


class DonorMatch(Base):
    __tablename__ = "donor_matches"
    __table_args__ = (UniqueConstraint("request_id", "donor_id", name="uq_match_request_donor"),)

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("blood_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    donor_id = Column(Integer, ForeignKey("donor_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    distance_km = Column(Float, nullable=True)  # None when the donor has no saved coordinates
    match_score = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(MatchStatus, name="match_status"), default=MatchStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    responded_at = Column(DateTime, nullable=True)

    request = relationship("BloodRequest", back_populates="matches")
    donor = relationship("DonorProfile", back_populates="matches")
