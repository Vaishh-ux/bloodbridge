"""Donor matching engine.

Blood compatibility (red-cell) is a hard filter. Remaining donors are filtered by availability,
system screening criteria and distance, then ranked with configurable weights.
"""
from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.blood_request import ACTIVE_STATUSES, BloodRequest, EmergencyLevel, RequestStatus
from app.models.donor import DonorProfile
from app.models.match import DonorMatch, MatchStatus
from app.models.user import User
from app.services.distance_service import calculate_haversine_distance
from app.services.eligibility_service import donor_eligibility

# recipient -> donor groups whose red cells the recipient can receive
COMPATIBILITY_MATRIX: Dict[str, List[str]] = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}


def is_blood_compatible(recipient_bg: str, donor_bg: str) -> bool:
    return donor_bg.upper() in COMPATIBILITY_MATRIX.get(recipient_bg.upper(), [])


def compatible_donor_groups(recipient_bg: str) -> List[str]:
    return list(COMPATIBILITY_MATRIX.get(recipient_bg.upper(), []))


def can_donate_to(donor_bg: str) -> List[str]:
    return [r for r, donors in COMPATIBILITY_MATRIX.items() if donor_bg.upper() in donors]


EMERGENCY_SCORES = {
    EmergencyLevel.CRITICAL: 100.0,
    EmergencyLevel.HIGH: 80.0,
    EmergencyLevel.MEDIUM: 60.0,
    EmergencyLevel.NORMAL: 40.0,
}


def distance_score(distance_km: Optional[float], max_km: float) -> float:
    if distance_km is None:  # same city but no coordinates saved
        return 40.0
    if distance_km >= max_km:
        return 0.0
    return 100.0 * (1 - distance_km / max_km)


def calculate_match_score(
    distance_km: Optional[float],
    available: bool,
    eligible: bool,
    emergency_level: EmergencyLevel,
    successful_donations: int = 0,
    reliability: Optional[float] = None,
    max_km: Optional[float] = None,
) -> float:
    if not eligible or not available:
        return 0.0
    max_km = max_km or settings.MAX_MATCH_DISTANCE_KM
    w = {
        "d": settings.WEIGHT_DISTANCE, "a": settings.WEIGHT_AVAILABILITY, "e": settings.WEIGHT_ELIGIBILITY,
        "p": settings.WEIGHT_EMERGENCY_PRIORITY, "h": settings.WEIGHT_RESPONSE_HISTORY, "r": settings.WEIGHT_RELIABILITY,
    }
    total_w = sum(w.values()) or 1.0
    score = (
        distance_score(distance_km, max_km) * w["d"]
        + 100.0 * w["a"]
        + 100.0 * w["e"]
        + EMERGENCY_SCORES.get(emergency_level, 50.0) * w["p"]
        + min(100.0, successful_donations * 20.0) * w["h"]
        + (50.0 if reliability is None else reliability) * w["r"]
    )
    return round(score / total_w, 1)


def _reliability_by_donor(db: Session, donor_ids: List[int]) -> Dict[int, float]:
    """Share of responded matches the donor accepted (None if never responded)."""
    if not donor_ids:
        return {}
    counts = defaultdict(lambda: [0, 0])
    rows = db.query(DonorMatch.donor_id, DonorMatch.status).filter(
        DonorMatch.donor_id.in_(donor_ids),
        DonorMatch.status.in_([MatchStatus.ACCEPTED, MatchStatus.CONFIRMED, MatchStatus.REJECTED]),
    ).all()
    for donor_id, status in rows:
        counts[donor_id][1] += 1
        if status != MatchStatus.REJECTED:
            counts[donor_id][0] += 1
    return {d: 100.0 * a / t for d, (a, t) in counts.items() if t}


def _location_ok(request: BloodRequest, donor: DonorProfile, max_km: float):
    """Returns (in_range, distance_km_or_None)."""
    if donor.latitude is not None and donor.longitude is not None:
        d = calculate_haversine_distance(request.latitude, request.longitude, donor.latitude, donor.longitude)
        return d <= max_km, d
    same_city = (donor.city or "").strip().lower() == (request.city or "").strip().lower()
    return same_city, None


def evaluate_donor_for_request(db: Session, request: BloodRequest, donor: DonorProfile, max_km: float = None):
    """Returns (ok, reason, distance_km, score)."""
    max_km = max_km or settings.MAX_MATCH_DISTANCE_KM
    if not is_blood_compatible(request.blood_group, donor.blood_group):
        return False, f"{donor.blood_group} red cells are not compatible with a {request.blood_group} recipient.", None, 0.0
    if not donor.available:
        return False, "This donor is currently marked unavailable.", None, 0.0
    eligible, reason = donor_eligibility(donor)
    if not eligible:
        return False, reason, None, 0.0
    in_range, dist = _location_ok(request, donor, max_km)
    reliability = _reliability_by_donor(db, [donor.id]).get(donor.id)
    score = calculate_match_score(dist, True, True, request.emergency_level, donor.successful_donations, reliability, max_km)
    return True, "Eligible for screening.", dist, score


def run_donor_matching(db: Session, request: BloodRequest, max_distance_km: float = None) -> List[DonorMatch]:
    """Create PENDING matches for every compatible, available, eligible donor in range.

    Returns the newly created matches, best first. Existing matches are left untouched.
    """
    max_km = max_distance_km or settings.MAX_MATCH_DISTANCE_KM
    if request.status not in ACTIVE_STATUSES:
        return []

    groups = compatible_donor_groups(request.blood_group)
    donors = (
        db.query(DonorProfile)
        .join(User, User.id == DonorProfile.user_id)
        .filter(
            DonorProfile.available.is_(True),
            DonorProfile.blood_group.in_(groups),
            User.is_active.is_(True),
            User.is_blocked.is_(False),
        )
        .all()
    )
    existing = {m.donor_id for m in db.query(DonorMatch.donor_id).filter(DonorMatch.request_id == request.id)}
    reliability = _reliability_by_donor(db, [d.id for d in donors])

    created: List[DonorMatch] = []
    for donor in donors:
        if donor.id in existing or donor.user_id == request.created_by_user_id:
            continue
        eligible, _ = donor_eligibility(donor)
        if not eligible:
            continue
        in_range, dist = _location_ok(request, donor, max_km)
        if not in_range:
            continue
        score = calculate_match_score(
            dist, True, True, request.emergency_level, donor.successful_donations, reliability.get(donor.id), max_km
        )
        match = DonorMatch(request_id=request.id, donor_id=donor.id, distance_km=dist, match_score=score,
                           status=MatchStatus.PENDING)
        db.add(match)
        created.append(match)

    has_any = bool(created) or bool(existing)
    if request.status in (RequestStatus.REQUESTED, RequestStatus.SEARCHING):
        request.status = RequestStatus.DONOR_FOUND if has_any else RequestStatus.SEARCHING

    db.commit()
    for m in created:
        db.refresh(m)
    created.sort(key=lambda m: m.match_score, reverse=True)
    return created


def match_donor_to_open_requests(db: Session, donor: DonorProfile) -> List[DonorMatch]:
    """When a donor registers or becomes available, match them against open requests."""
    if not donor.available or not donor_eligibility(donor)[0]:
        return []
    recipient_groups = can_donate_to(donor.blood_group)
    open_requests = db.query(BloodRequest).filter(
        BloodRequest.status.in_([RequestStatus.REQUESTED, RequestStatus.SEARCHING, RequestStatus.DONOR_FOUND]),
        BloodRequest.blood_group.in_(recipient_groups),
    ).all()
    already = {m.request_id for m in db.query(DonorMatch.request_id).filter(DonorMatch.donor_id == donor.id)}
    reliability = _reliability_by_donor(db, [donor.id]).get(donor.id)
    created = []
    for req in open_requests:
        if req.id in already or req.created_by_user_id == donor.user_id:
            continue
        in_range, dist = _location_ok(req, donor, settings.MAX_MATCH_DISTANCE_KM)
        if not in_range:
            continue
        score = calculate_match_score(dist, True, True, req.emergency_level, donor.successful_donations, reliability)
        m = DonorMatch(request_id=req.id, donor_id=donor.id, distance_km=dist, match_score=score, status=MatchStatus.PENDING)
        db.add(m)
        created.append(m)
        if req.status == RequestStatus.SEARCHING:
            req.status = RequestStatus.DONOR_FOUND
    db.commit()
    for m in created:
        db.refresh(m)
    return created
