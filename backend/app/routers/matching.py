from app.timeutil import utcnow
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models.blood_request import RequestStatus
from app.models.donation import Donation
from app.models.match import DonorMatch, MatchStatus
from app.models.user import User, UserRole
from app.routers.requests import can_manage, get_request_or_404, notify_matched_donors, notify_request_parties
from app.services.audit import audit
from app.services.eligibility_service import donor_eligibility
from app.services.matching_service import run_donor_matching
from app.services.notification_service import create_notification
from app.services.privacy import initials_name

router = APIRouter(prefix="/matching", tags=["Matching Engine"])


def _match_or_404(db: Session, match_id: int) -> DonorMatch:
    m = db.get(DonorMatch, match_id)
    if not m:
        raise HTTPException(404, "Match not found.")
    return m


@router.get("/{request_id}")
def get_request_matches(request_id: int, current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Matched donors for a request (owner, linked facility or admin only).

    Contact details are shared only for donors who have accepted.
    """
    req = get_request_or_404(db, request_id)
    if not can_manage(current_user, req):
        raise HTTPException(403, "You are not authorized to view matches for this request.")
    out = []
    for m in req.matches:
        d = m.donor
        shared = m.status in (MatchStatus.ACCEPTED, MatchStatus.CONFIRMED)
        out.append({
            "match_id": m.id, "request_id": m.request_id,
            "distance_km": round(m.distance_km, 1) if m.distance_km is not None else None,
            "match_score": m.match_score, "match_status": m.status.value,
            "donor_name": (d.user.name if shared else initials_name(d.user.name)) if d and d.user else "Donor",
            "donor_phone": d.user.phone if shared and d and d.user else None,
            "donor_blood_group": d.blood_group if d else None,
            "city": d.city if d else None,
            "eligible": donor_eligibility(d)[0] if d else False,
            "responded_at": m.responded_at.isoformat() if m.responded_at else None,
        })
    order = {"CONFIRMED": 0, "ACCEPTED": 1, "PENDING": 2, "REJECTED": 3, "CLOSED": 4}
    out.sort(key=lambda x: (order[x["match_status"]], -x["match_score"]))
    return out


@router.post("/{request_id}")
async def rerun_matching(request_id: int, current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    req = get_request_or_404(db, request_id)
    if not can_manage(current_user, req):
        raise HTTPException(403, "You are not authorized to perform this action.")
    if not req.is_active:
        raise HTTPException(400, "This request is no longer active.")
    new = run_donor_matching(db, req)
    await notify_matched_donors(db, req, new)
    return {"new_matches": len(new), "status": req.status.value}


@router.post("/{match_id}/accept")
async def accept_match(match_id: int, request: Request,
                       current_user: User = Depends(require_roles([UserRole.DONOR])), db: Session = Depends(get_db)):
    m = _match_or_404(db, match_id)
    donor = m.donor
    if not donor or donor.user_id != current_user.id:
        raise HTTPException(403, "You can only respond to your own matches.")
    req = m.request
    if req.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED):
        raise HTTPException(400, "This request is no longer active.")
    if m.status in (MatchStatus.ACCEPTED, MatchStatus.CONFIRMED):
        raise HTTPException(400, "You have already accepted this request.")
    if m.status == MatchStatus.CLOSED:
        raise HTTPException(400, "This match has been closed.")
    eligible, reason = donor_eligibility(donor)
    if not donor.available or not eligible:
        raise HTTPException(400, reason if not eligible else "Set your availability to Available before accepting.")

    m.status = MatchStatus.ACCEPTED
    m.responded_at = utcnow()
    if req.status in (RequestStatus.REQUESTED, RequestStatus.SEARCHING, RequestStatus.DONOR_FOUND):
        req.status = RequestStatus.DONOR_ACCEPTED
    audit(db, current_user.id, "MATCH_ACCEPTED", "donor_match", m.id, f"request={req.id}", request)
    db.commit()
    await notify_request_parties(db, req, "🎉 Donor Accepted Your Request!",
                                 f"{current_user.name} ({donor.blood_group}) accepted request #{req.id}. "
                                 f"Open 'View Matched Donors' to see their contact number.", "DONOR_ACCEPTED")
    return {"message": "Match accepted. Please contact the hospital before travelling.",
            "status": m.status.value, "hospital_address": req.hospital_address,
            "hospital_phone": req.hospital.phone if req.hospital else None}


@router.post("/{match_id}/reject")
async def reject_match(match_id: int, current_user: User = Depends(require_roles([UserRole.DONOR])),
                       db: Session = Depends(get_db)):
    m = _match_or_404(db, match_id)
    if not m.donor or m.donor.user_id != current_user.id:
        raise HTTPException(403, "You can only respond to your own matches.")
    if m.status == MatchStatus.CONFIRMED:
        raise HTTPException(400, "This donation has already been confirmed.")
    was_accepted = m.status == MatchStatus.ACCEPTED
    m.status = MatchStatus.REJECTED
    m.responded_at = utcnow()
    req = m.request
    if was_accepted and req.status == RequestStatus.DONOR_ACCEPTED:
        still = any(x.status == MatchStatus.ACCEPTED for x in req.matches if x.id != m.id)
        if not still:
            req.status = RequestStatus.DONOR_FOUND
    db.commit()
    if was_accepted:
        await notify_request_parties(db, req, "Donor Withdrew",
                                     f"A donor withdrew from request #{req.id}. Other matched donors remain notified.",
                                     "DONOR_REJECTED")
    return {"message": "Response recorded. Thank you for letting us know.", "status": m.status.value}


class ConfirmDonation(BaseModel):
    units: int = Field(default=1, ge=1, le=4)


@router.post("/{match_id}/confirm")
async def confirm_donation(match_id: int, body: ConfirmDonation, request: Request,
                           current_user: User = Depends(require_roles([UserRole.HOSPITAL, UserRole.ADMIN])),
                           db: Session = Depends(get_db)):
    """Facility staff confirm that an accepted donor actually donated."""
    m = _match_or_404(db, match_id)
    req = m.request
    is_facility = (current_user.role == UserRole.HOSPITAL and current_user.hospital_profile
                   and req.hospital_id == current_user.hospital_profile.id)
    if not (is_facility or current_user.role == UserRole.ADMIN):
        raise HTTPException(403, "Only the hospital handling this request can confirm donations.")
    if m.status != MatchStatus.ACCEPTED:
        raise HTTPException(400, "Only donors who accepted the request can be confirmed.")
    if req.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED):
        raise HTTPException(400, "This request is no longer active.")

    donor = m.donor
    today = date.today()
    m.status = MatchStatus.CONFIRMED
    donation = Donation(donor_id=donor.id, request_id=req.id, hospital_id=req.hospital_id, match_id=m.id,
                        confirmed_by_user_id=current_user.id, blood_group=donor.blood_group, units=body.units,
                        donation_date=today)
    db.add(donation)
    db.flush()
    donation.certificate_number = f"BB-{today:%Y%m%d}-{donation.id:06d}"
    donor.last_donation_date = today
    donor.total_donations = (donor.total_donations or 0) + 1
    donor.successful_donations = (donor.successful_donations or 0) + 1
    donor.available = False  # resting period; donor can switch back when eligible

    fulfilled = db.query(func.coalesce(func.sum(Donation.units), 0)).filter(Donation.request_id == req.id).scalar()
    if fulfilled >= req.units_required:
        req.status = RequestStatus.COMPLETED
        req.completed_at = utcnow()
        for other in req.matches:
            if other.status == MatchStatus.PENDING:
                other.status = MatchStatus.CLOSED
    else:
        req.status = RequestStatus.HOSPITAL_CONFIRMED
    audit(db, current_user.id, "DONATION_CONFIRMED", "donation", donation.id,
          f"request={req.id} units={body.units}", request)
    db.commit()

    await create_notification(db, donor.user_id, "❤️ Thank You for Donating!",
                              f"Your donation for request #{req.id} was confirmed. Reference "
                              f"{donation.certificate_number}.", "DONATION_COMPLETED", req.id)
    title = "✅ Blood Donation Confirmed" if req.status == RequestStatus.HOSPITAL_CONFIRMED else "✅ Request Completed"
    await notify_request_parties(db, req, title,
                                 f"{fulfilled} of {req.units_required} unit(s) confirmed for request #{req.id}.",
                                 "HOSPITAL_CONFIRMED", exclude_user_id=current_user.id)
    return {"message": "Donation confirmed.", "request_status": req.status.value, "units_fulfilled": fulfilled,
            "certificate_number": donation.certificate_number}
