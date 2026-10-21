from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.constants import MEDICAL_DISCLAIMER
from app.config import settings
from app.database import get_db
from app.models.blood_request import ACTIVE_STATUSES, BloodRequest, RequestStatus
from app.models.donation import Donation
from app.models.donor import DonorProfile
from app.models.hospital import FacilityType, Hospital
from app.models.match import DonorMatch, MatchStatus
from app.models.user import User
from app.services.eligibility_service import donor_eligibility

router = APIRouter(prefix="/stats", tags=["Public statistics"])


@router.get("/public")
def public_stats(db: Session = Depends(get_db)):
    """Live counts computed from the database (no estimates or padding)."""
    donors = db.query(DonorProfile).join(User, User.id == DonorProfile.user_id) \
        .filter(User.is_active.is_(True), User.is_blocked.is_(False)).all()
    available = sum(1 for d in donors if d.available and donor_eligibility(d)[0])
    facilities = db.query(Hospital).join(User, User.id == Hospital.user_id).filter(User.is_blocked.is_(False)).all()
    return {
        "registered_donors": len(donors),
        "available_donors": available,
        "active_requests": db.query(BloodRequest).filter(BloodRequest.status.in_(ACTIVE_STATUSES),
                                                         BloodRequest.is_suspicious.is_(False)).count(),
        "fulfilled_requests": db.query(BloodRequest).filter(BloodRequest.status == RequestStatus.COMPLETED).count(),
        "successful_matches": db.query(DonorMatch).filter(
            DonorMatch.status.in_([MatchStatus.ACCEPTED, MatchStatus.CONFIRMED])).count(),
        "confirmed_donations": db.query(Donation).count(),
        "hospitals": sum(1 for h in facilities if h.facility_type == FacilityType.HOSPITAL),
        "blood_banks": sum(1 for h in facilities if h.facility_type == FacilityType.BLOOD_BANK),
        "verified_facilities": sum(1 for h in facilities if h.verified),
    }


@router.get("/config")
def public_config():
    """Screening settings the frontend shows in the awareness section."""
    return {
        "min_donation_interval_days": settings.MIN_DONATION_INTERVAL_DAYS,
        "min_donor_age": settings.MIN_DONOR_AGE,
        "max_donor_age": settings.MAX_DONOR_AGE,
        "max_match_distance_km": settings.MAX_MATCH_DISTANCE_KM,
        "disclaimer": MEDICAL_DISCLAIMER,
    }
