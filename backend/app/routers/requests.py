from app.timeutil import utcnow
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth import get_optional_user, require_roles
from app.database import get_db
from app.models.blood_request import (ACTIVE_STATUSES, URGENCY_ORDER, BloodRequest, EmergencyLevel,
                                      RequestStatus)
from app.models.donor import DonorProfile
from app.models.hospital import Hospital
from app.models.match import DonorMatch, MatchStatus
from app.models.user import User, UserRole
from app.schemas.blood_request import BloodRequestCreate, BloodRequestUpdate
from app.schemas.common import clean_blood_group
from app.services.audit import audit
from app.services.matching_service import evaluate_donor_for_request, run_donor_matching
from app.services.notification_service import create_notification, push_event
from app.services.privacy import private_request, public_request
from app.services.websocket import manager
from app.config import settings

router = APIRouter(prefix="/requests", tags=["Blood Requests"])

REQUESTERS = [UserRole.PATIENT, UserRole.HOSPITAL, UserRole.ADMIN]


def can_manage(user: Optional[User], req: BloodRequest) -> bool:
    if user is None:
        return False
    if user.role == UserRole.ADMIN or req.created_by_user_id == user.id:
        return True
    return bool(user.role == UserRole.HOSPITAL and user.hospital_profile
                and req.hospital_id == user.hospital_profile.id)


def get_request_or_404(db: Session, request_id: int) -> BloodRequest:
    req = db.get(BloodRequest, request_id)
    if not req:
        raise HTTPException(404, "Request not found.")
    return req


async def notify_request_parties(db: Session, req: BloodRequest, title: str, message: str, ntype: str,
                                 exclude_user_id: Optional[int] = None):
    """Notify the request owner and the linked facility account (if any)."""
    targets = {req.created_by_user_id}
    if req.hospital and req.hospital.user_id:
        targets.add(req.hospital.user_id)
    for uid in targets:
        if uid and uid != exclude_user_id:
            await create_notification(db, uid, title, message, ntype, req.id)
            await push_event(uid, "REQUEST_UPDATED", {"id": req.id, "status": req.status.value})


async def notify_matched_donors(db: Session, req: BloodRequest, matches):
    for m in matches[: settings.NOTIFY_TOP_N_DONORS]:
        if m.donor and m.donor.user_id:
            dist = f"{m.distance_km:.1f} km away" if m.distance_km is not None else f"in {req.city}"
            await create_notification(
                db, m.donor.user_id, "🚨 Emergency Blood Request Available",
                f"{req.emergency_level.value} request for {req.blood_group} ({req.units_required} unit(s)) at "
                f"{req.hospital_name}, {dist}. Match score {m.match_score}%.", "MATCH_FOUND", req.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_blood_request(request_in: BloodRequestCreate, request: Request,
                               current_user: User = Depends(require_roles(REQUESTERS)),
                               db: Session = Depends(get_db)):
    hospital: Optional[Hospital] = None
    if current_user.role == UserRole.HOSPITAL:
        hospital = current_user.hospital_profile
    elif request_in.hospital_id is not None:
        hospital = db.get(Hospital, request_in.hospital_id)
        if not hospital:
            raise HTTPException(400, "Selected hospital was not found.")

    def pick(manual, from_hosp):
        return (manual or "").strip() or from_hosp

    lat = request_in.latitude if request_in.latitude is not None else (hospital.latitude if hospital else None)
    lng = request_in.longitude if request_in.longitude is not None else (hospital.longitude if hospital else None)
    if lat is None or lng is None:
        raise HTTPException(400, "Hospital location is required for donor matching.")

    req = BloodRequest(
        created_by_user_id=current_user.id,
        patient_id=current_user.patient_profile.id if current_user.patient_profile else None,
        hospital_id=hospital.id if hospital else None,
        patient_name=(request_in.patient_name or "").strip() or None,
        hospital_name=pick(request_in.hospital_name, hospital.name if hospital else None),
        hospital_address=pick(request_in.hospital_address, hospital.address if hospital else None),
        city=pick(request_in.city, hospital.city if hospital else None),
        state=pick(request_in.state, hospital.state if hospital else None),
        blood_group=request_in.blood_group,
        units_required=request_in.units_required,
        emergency_level=request_in.emergency_level,
        latitude=lat, longitude=lng,
        required_date=request_in.required_date.isoformat(),
        required_time=request_in.required_time,
        status=RequestStatus.REQUESTED,
        notes=(request_in.notes or "").strip() or None,
    )
    if not all([req.hospital_name, req.hospital_address, req.city, req.state]):
        raise HTTPException(400, "Hospital name, address, city and state are required.")
    db.add(req)
    db.flush()
    audit(db, current_user.id, "REQUEST_CREATED", "blood_request", req.id,
          f"{req.blood_group} x{req.units_required} {req.emergency_level.value}", request)
    db.commit()
    db.refresh(req)

    matches = run_donor_matching(db, req)
    db.refresh(req)

    if matches:
        msg = (f"Your request for {req.units_required} unit(s) of {req.blood_group} matched "
               f"{len(matches)} compatible donor(s). They are being notified now.")
    else:
        msg = ("No compatible, available donor was found within range yet. Your request stays open and "
               "new donors will be matched automatically. Please also contact the hospital blood bank directly.")
    await create_notification(db, current_user.id, "Blood Request Broadcast Active", msg, "REQUEST_BROADCAST", req.id)
    if req.hospital and req.hospital.user_id and req.hospital.user_id != current_user.id:
        await create_notification(db, req.hospital.user_id, "New Blood Request For Your Facility",
                                  f"Request #{req.id}: {req.blood_group} x{req.units_required} "
                                  f"({req.emergency_level.value}).", "REQUEST_CREATED", req.id)
    await notify_matched_donors(db, req, matches)
    await manager.broadcast({"event": "REQUEST_NEW", "data": public_request(req)})

    out = private_request(req)
    out["matched_donors_count"] = len(matches)
    out["message"] = msg
    return out


@router.get("")
def list_requests(
    city: Optional[str] = None,
    blood_group: Optional[str] = None,
    emergency_level: Optional[EmergencyLevel] = None,
    status_filter: Optional[str] = Query(None, alias="status",
                                         description="ACTIVE (default), ALL, or a specific status"),
    hospital_id: Optional[int] = None,
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Public feed. Returns the privacy-safe view of each request, most urgent first."""
    q = db.query(BloodRequest).filter(BloodRequest.is_suspicious.is_(False))
    st = (status_filter or "ACTIVE").upper()
    if st == "ACTIVE":
        q = q.filter(BloodRequest.status.in_(ACTIVE_STATUSES))
    elif st != "ALL":
        try:
            q = q.filter(BloodRequest.status == RequestStatus(st))
        except ValueError:
            raise HTTPException(400, "Unknown status filter.")
    if city:
        q = q.filter(BloodRequest.city.ilike(f"%{city.strip()}%"))
    if blood_group:
        try:
            q = q.filter(BloodRequest.blood_group == clean_blood_group(blood_group))
        except ValueError as e:
            raise HTTPException(400, str(e))
    if emergency_level:
        q = q.filter(BloodRequest.emergency_level == emergency_level)
    if hospital_id:
        q = q.filter(BloodRequest.hospital_id == hospital_id)
    reqs = q.order_by(BloodRequest.created_at.desc()).limit(limit).all()
    reqs.sort(key=lambda r: (URGENCY_ORDER[r.emergency_level], -r.created_at.timestamp()))
    return [public_request(r) for r in reqs]


@router.get("/mine")
def my_requests(current_user: User = Depends(require_roles(REQUESTERS)), db: Session = Depends(get_db)):
    reqs = db.query(BloodRequest).filter(BloodRequest.created_by_user_id == current_user.id) \
        .order_by(BloodRequest.created_at.desc()).all()
    out = []
    for r in reqs:
        item = private_request(r)
        item["matches_total"] = len(r.matches)
        item["matches_accepted"] = sum(1 for m in r.matches if m.status in (MatchStatus.ACCEPTED, MatchStatus.CONFIRMED))
        item["units_fulfilled"] = sum(d.units for d in r.donations)
        out.append(item)
    return out


@router.get("/{request_id}")
def get_request(request_id: int, db: Session = Depends(get_db),
                current_user: Optional[User] = Depends(get_optional_user)):
    req = get_request_or_404(db, request_id)
    if can_manage(current_user, req):
        out = private_request(req)
        out["units_fulfilled"] = sum(d.units for d in req.donations)
        return out
    if req.is_suspicious:
        raise HTTPException(404, "Request not found.")
    return public_request(req)


@router.put("/{request_id}")
async def update_request(request_id: int, payload: BloodRequestUpdate,
                         current_user: User = Depends(require_roles(REQUESTERS)), db: Session = Depends(get_db)):
    req = get_request_or_404(db, request_id)
    if not can_manage(current_user, req):
        raise HTTPException(403, "You are not authorized to perform this action.")
    if not req.is_active:
        raise HTTPException(400, "Only active requests can be edited.")
    data = payload.model_dump(exclude_unset=True)
    if "required_date" in data and data["required_date"] is not None:
        data["required_date"] = data["required_date"].isoformat()
    for k, v in data.items():
        if v is not None or k == "notes":
            setattr(req, k, v)
    db.commit()
    db.refresh(req)
    return private_request(req)


async def _cancel(db: Session, req: BloodRequest, user: User, request: Request):
    if req.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED):
        raise HTTPException(400, f"Request is already {req.status.value.lower()}.")
    req.status = RequestStatus.CANCELLED
    affected = []
    for m in req.matches:
        if m.status in (MatchStatus.PENDING, MatchStatus.ACCEPTED):
            affected.append(m)
            m.status = MatchStatus.CLOSED
    audit(db, user.id, "REQUEST_CANCELLED", "blood_request", req.id, None, request)
    db.commit()
    for m in affected:
        await create_notification(db, m.donor.user_id, "Request Cancelled",
                                  f"Request #{req.id} for {req.blood_group} at {req.hospital_name} was cancelled. "
                                  f"Thank you for your willingness to help.", "REQUEST_CANCELLED", req.id)
    await notify_request_parties(db, req, "Request Cancelled", f"Request #{req.id} has been cancelled.",
                                 "REQUEST_CANCELLED")
    return {"message": "Request cancelled successfully.", "status": req.status.value}


@router.post("/{request_id}/cancel")
async def cancel_request(request_id: int, request: Request,
                         current_user: User = Depends(require_roles(REQUESTERS)), db: Session = Depends(get_db)):
    req = get_request_or_404(db, request_id)
    if not can_manage(current_user, req):
        raise HTTPException(403, "You are not authorized to perform this action.")
    return await _cancel(db, req, current_user, request)


@router.delete("/{request_id}")
async def delete_request(request_id: int, request: Request,
                         current_user: User = Depends(require_roles(REQUESTERS)), db: Session = Depends(get_db)):
    """Soft delete = cancel. Records are kept for audit purposes."""
    return await cancel_request(request_id, request, current_user, db)


@router.post("/{request_id}/fulfilled")
async def mark_fulfilled(request_id: int, request: Request,
                         current_user: User = Depends(require_roles(REQUESTERS)), db: Session = Depends(get_db)):
    """Requester marks the need as met (e.g. arranged through the hospital directly)."""
    req = get_request_or_404(db, request_id)
    if not can_manage(current_user, req):
        raise HTTPException(403, "You are not authorized to perform this action.")
    if not req.is_active:
        raise HTTPException(400, f"Request is already {req.status.value.lower()}.")
    req.status = RequestStatus.COMPLETED
    req.completed_at = utcnow()
    for m in req.matches:
        if m.status == MatchStatus.PENDING:
            m.status = MatchStatus.CLOSED
    audit(db, current_user.id, "REQUEST_FULFILLED", "blood_request", req.id, None, request)
    db.commit()
    await notify_request_parties(db, req, "Request Completed", f"Request #{req.id} was marked as fulfilled.",
                                 "REQUEST_COMPLETED", exclude_user_id=current_user.id)
    return {"message": "Request marked as fulfilled.", "status": req.status.value}


@router.post("/{request_id}/respond")
async def donor_volunteer(request_id: int, current_user: User = Depends(require_roles([UserRole.DONOR])),
                          db: Session = Depends(get_db)):
    """A donor offers to donate for a request from the public urgent feed."""
    req = get_request_or_404(db, request_id)
    if req.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED):
        raise HTTPException(400, "This request is no longer active.")
    donor = db.query(DonorProfile).filter(DonorProfile.user_id == current_user.id).first()
    if not donor:
        raise HTTPException(404, "Donor profile not found.")
    if req.created_by_user_id == current_user.id:
        raise HTTPException(400, "You cannot respond to your own request.")
    ok, reason, dist, score = evaluate_donor_for_request(db, req, donor)
    if not ok:
        raise HTTPException(400, reason)

    match = db.query(DonorMatch).filter(DonorMatch.request_id == req.id, DonorMatch.donor_id == donor.id).first()
    if match and match.status in (MatchStatus.ACCEPTED, MatchStatus.CONFIRMED):
        raise HTTPException(400, "You have already accepted this request.")
    if not match:
        match = DonorMatch(request_id=req.id, donor_id=donor.id, distance_km=dist, match_score=score)
        db.add(match)
    match.status = MatchStatus.ACCEPTED
    match.responded_at = utcnow()
    if req.status in (RequestStatus.REQUESTED, RequestStatus.SEARCHING, RequestStatus.DONOR_FOUND):
        req.status = RequestStatus.DONOR_ACCEPTED
    db.commit()
    db.refresh(match)
    await notify_request_parties(db, req, "🎉 A Donor Accepted Your Request!",
                                 f"A {donor.blood_group} donor volunteered for request #{req.id}. "
                                 f"View matched donors for contact details.", "DONOR_ACCEPTED")
    return {"message": "Thank you! The requester and hospital have been notified.", "match_id": match.id,
            "status": match.status.value}
