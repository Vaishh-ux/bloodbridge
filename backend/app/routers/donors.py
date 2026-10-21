from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models.blood_request import URGENCY_ORDER, BloodRequest, EmergencyLevel, RequestStatus
from app.models.donation import Donation
from app.models.donor import DonorProfile
from app.models.match import DonorMatch, MatchStatus
from app.models.user import User, UserRole
from app.schemas.common import clean_blood_group
from app.schemas.donor import AvailabilityUpdate, DonorProfileUpdate
from app.services.distance_service import calculate_haversine_distance
from app.services.eligibility_service import donor_eligibility
from app.services.matching_service import (can_donate_to, compatible_donor_groups, evaluate_donor_for_request,
                                           match_donor_to_open_requests)
from app.services.notification_service import create_notification
from app.services.privacy import initials_name, public_request

router = APIRouter(prefix="/donors", tags=["Donors"])


def _bg_or_400(v: Optional[str]) -> Optional[str]:
    try:
        return clean_blood_group(v)
    except ValueError as e:
        raise HTTPException(400, str(e))


def _my_donor(db: Session, user: User) -> DonorProfile:
    donor = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if not donor:
        raise HTTPException(404, "Donor profile not found.")
    return donor


@router.get("")
def search_donors(
    blood_group: Optional[str] = Query(None, description="Exact donor blood group"),
    compatible_with: Optional[str] = Query(None, description="Recipient blood group; returns compatible donors"),
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    available_only: bool = True,
    eligible_only: bool = False,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = Query(25.0, gt=0, le=500),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Privacy-safe donor search.

    Never returns names in full, phone numbers, addresses or coordinates. To reach donors,
    create a blood request: matched donors are notified and decide whether to share contact details.
    """
    q = db.query(DonorProfile).join(User, User.id == DonorProfile.user_id).filter(
        User.is_active.is_(True), User.is_blocked.is_(False))
    bg = _bg_or_400(blood_group)
    if bg:
        q = q.filter(DonorProfile.blood_group == bg)
    recip = _bg_or_400(compatible_with)
    if recip:
        q = q.filter(DonorProfile.blood_group.in_(compatible_donor_groups(recip)))
    if available_only:
        q = q.filter(DonorProfile.available.is_(True))
    if city:
        q = q.filter(DonorProfile.city.ilike(f"%{city.strip()}%"))
    if pincode:
        q = q.filter(DonorProfile.pincode.ilike(f"{pincode.strip()}%"))

    use_distance = lat is not None and lng is not None
    results = []
    for d in q.all():
        eligible, reason = donor_eligibility(d)
        if eligible_only and not eligible:
            continue
        dist = None
        if use_distance:
            if d.latitude is None:
                continue
            dist = calculate_haversine_distance(lat, lng, d.latitude, d.longitude)
            if dist > radius_km:
                continue
        results.append({
            "donor_ref": d.id,
            "display_name": initials_name(d.user.name if d.user else None),
            "blood_group": d.blood_group,
            "city": d.city,
            "area_pincode": (d.pincode[:3] + "***") if d.pincode else None,
            "available": d.available,
            "eligible": eligible,
            "eligibility_note": reason,
            "distance_km": round(dist, 1) if dist is not None else None,
            "successful_donations": d.successful_donations,
        })
    results.sort(key=lambda r: (not r["eligible"], r["distance_km"] if r["distance_km"] is not None else 1e9))
    return {"count": len(results), "donors": results[:limit]}


@router.get("/me")
def my_profile(current_user: User = Depends(require_roles([UserRole.DONOR])), db: Session = Depends(get_db)):
    d = _my_donor(db, current_user)
    eligible, reason = donor_eligibility(d)
    return {
        "id": d.id, "blood_group": d.blood_group, "can_donate_to": can_donate_to(d.blood_group),
        "city": d.city, "state": d.state, "pincode": d.pincode, "address": d.address, "gender": d.gender,
        "date_of_birth": d.date_of_birth.isoformat() if d.date_of_birth else None,
        "latitude": d.latitude, "longitude": d.longitude, "available": d.available,
        "last_donation_date": d.last_donation_date.isoformat() if d.last_donation_date else None,
        "screening_passed": d.screening_passed, "eligible": eligible, "eligibility_reason": reason,
        "total_donations": d.total_donations, "successful_donations": d.successful_donations,
        "phone": current_user.phone,
    }


@router.put("/profile")
async def update_profile(payload: DonorProfileUpdate, current_user: User = Depends(require_roles([UserRole.DONOR])),
                         db: Session = Depends(get_db)):
    d = _my_donor(db, current_user)
    data = payload.model_dump(exclude_unset=True)
    if "phone" in data and data["phone"]:
        current_user.phone = data.pop("phone")
    data.pop("phone", None)
    if "meets_basic_criteria" in data:
        d.screening_passed = bool(data.pop("meets_basic_criteria"))
    for k, v in data.items():
        if k in ("city", "state") and v is None:
            continue
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    await _notify_new_matches(db, d)
    return my_profile(current_user, db)


async def _notify_new_matches(db: Session, d: DonorProfile):
    for m in match_donor_to_open_requests(db, d):
        await create_notification(
            db, d.user_id, "🚨 Emergency Blood Request Available",
            f"A {m.request.emergency_level.value} request for {m.request.blood_group} at "
            f"{m.request.hospital_name}, {m.request.city} matches your blood group.", "MATCH_FOUND", m.request_id)


@router.put("/availability")
async def update_availability(payload: AvailabilityUpdate,
                              current_user: User = Depends(require_roles([UserRole.DONOR])),
                              db: Session = Depends(get_db)):
    d = _my_donor(db, current_user)
    d.available = payload.available
    db.commit()
    if d.available:
        await _notify_new_matches(db, d)
    eligible, reason = donor_eligibility(d)
    return {"available": d.available, "eligible": eligible, "eligibility_reason": reason}


@router.get("/matches")
def my_matches(current_user: User = Depends(require_roles([UserRole.DONOR])), db: Session = Depends(get_db)):
    d = _my_donor(db, current_user)
    out = []
    for m in db.query(DonorMatch).filter(DonorMatch.donor_id == d.id).all():
        req = m.request
        if not req:
            continue
        item = public_request(req)
        item.update({
            "match_id": m.id, "request_id": req.id, "distance_km": m.distance_km, "match_score": m.match_score,
            "match_status": m.status.value, "request_status": req.status.value,
            "created_at": m.created_at.isoformat(),
        })
        # Once the donor has accepted, they need the hospital's address/contact to go and donate.
        if m.status in (MatchStatus.ACCEPTED, MatchStatus.CONFIRMED):
            item["hospital_address"] = req.hospital_address
            item["latitude"], item["longitude"] = req.latitude, req.longitude
            item["hospital_phone"] = req.hospital.phone if req.hospital else None
        out.append(item)
    order = {MatchStatus.PENDING: 0, MatchStatus.ACCEPTED: 1, MatchStatus.CONFIRMED: 2, MatchStatus.REJECTED: 3, MatchStatus.CLOSED: 4}
    out.sort(key=lambda x: (order[MatchStatus(x["match_status"])], -x["match_score"]))
    return out


@router.get("/requests/nearby")
def nearby_requests_for_me(
    max_distance_km: float = Query(50.0, gt=0, le=1000),
    emergency_level: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.DONOR])),
    db: Session = Depends(get_db),
):
    """Open requests this donor's blood can serve, with distance and the donor's eligibility."""
    d = _my_donor(db, current_user)
    eligible, reason = donor_eligibility(d)
    q = db.query(BloodRequest).filter(
        BloodRequest.status.in_([RequestStatus.REQUESTED, RequestStatus.SEARCHING, RequestStatus.DONOR_FOUND,
                                 RequestStatus.DONOR_ACCEPTED, RequestStatus.HOSPITAL_CONFIRMED]),
        BloodRequest.blood_group.in_(can_donate_to(d.blood_group)),
    )
    if emergency_level:
        q = q.filter(BloodRequest.emergency_level == emergency_level)
    my_match = {m.request_id: m for m in db.query(DonorMatch).filter(DonorMatch.donor_id == d.id)}
    out = []
    for req in q.all():
        if req.created_by_user_id == current_user.id:
            continue
        dist = None
        if d.latitude is not None:
            dist = calculate_haversine_distance(d.latitude, d.longitude, req.latitude, req.longitude)
            if dist > max_distance_km:
                continue
        elif (d.city or "").lower() != (req.city or "").lower():
            continue
        item = public_request(req)
        m = my_match.get(req.id)
        item.update({"distance_km": round(dist, 1) if dist is not None else None,
                     "match_id": m.id if m else None, "match_status": m.status.value if m else None})
        out.append(item)
    out.sort(key=lambda x: (URGENCY_ORDER[EmergencyLevel(x["emergency_level"])], x["distance_km"] or 0))
    return {"eligible": eligible, "eligibility_reason": reason, "available": d.available, "requests": out}


@router.get("/donations")
def my_donations(current_user: User = Depends(require_roles([UserRole.DONOR])), db: Session = Depends(get_db)):
    d = _my_donor(db, current_user)
    rows = db.query(Donation).filter(Donation.donor_id == d.id).order_by(Donation.donation_date.desc()).all()
    return [{"id": r.id, "request_id": r.request_id, "hospital_name": r.hospital.name if r.hospital else None,
             "blood_group": r.blood_group, "units": r.units, "donation_date": r.donation_date.isoformat(),
             "certificate_number": r.certificate_number, "status": r.status} for r in rows]


@router.get("/check/{request_id}")
def check_my_eligibility_for(request_id: int, current_user: User = Depends(require_roles([UserRole.DONOR])),
                             db: Session = Depends(get_db)):
    d = _my_donor(db, current_user)
    req = db.get(BloodRequest, request_id)
    if not req:
        raise HTTPException(404, "Request not found.")
    ok, reason, dist, score = evaluate_donor_for_request(db, req, d)
    return {"ok": ok, "reason": reason, "distance_km": dist, "match_score": score}
