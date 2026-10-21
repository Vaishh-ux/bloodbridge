from app.timeutil import utcnow
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.blood_request import ACTIVE_STATUSES, BloodRequest, EmergencyLevel, RequestStatus
from app.models.donation import Donation
from app.models.donor import DonorProfile
from app.models.hospital import Hospital
from app.models.inventory import BloodInventory
from app.models.match import DonorMatch, MatchStatus
from app.models.user import User, UserRole
from app.services.audit import audit
from app.services.eligibility_service import donor_eligibility
from app.services.privacy import private_request

router = APIRouter(prefix="/admin", tags=["Admin Portal"])
admin_only = require_roles([UserRole.ADMIN])


@router.get("/dashboard")
def dashboard(current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return {
        "total_users": db.query(User).count(),
        "total_donors": db.query(DonorProfile).count(),
        "total_patients": db.query(User).filter(User.role == UserRole.PATIENT).count(),
        "total_hospitals": db.query(Hospital).count(),
        "unverified_hospitals": db.query(Hospital).filter(Hospital.verified.is_(False)).count(),
        "active_requests": db.query(BloodRequest).filter(BloodRequest.status.in_(ACTIVE_STATUSES)).count(),
        "completed_requests": db.query(BloodRequest).filter(BloodRequest.status == RequestStatus.COMPLETED).count(),
        "completed_donations": db.query(Donation).count(),
        "emergency_requests": db.query(BloodRequest).filter(BloodRequest.emergency_level == EmergencyLevel.CRITICAL,
                                                            BloodRequest.status.in_(ACTIVE_STATUSES)).count(),
        "flagged_requests": db.query(BloodRequest).filter(BloodRequest.is_suspicious.is_(True)).count(),
        "blocked_users": db.query(User).filter(User.is_blocked.is_(True)).count(),
    }


@router.get("/analytics")
def analytics(current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    bg = dict(db.query(DonorProfile.blood_group, func.count(DonorProfile.id)).group_by(DonorProfile.blood_group).all())
    demand = dict(db.query(BloodRequest.blood_group, func.count(BloodRequest.id)).group_by(BloodRequest.blood_group).all())
    emergency = {lvl.value: c for lvl, c in
                 db.query(BloodRequest.emergency_level, func.count(BloodRequest.id)).group_by(BloodRequest.emergency_level)}
    status = {st.value: c for st, c in db.query(BloodRequest.status, func.count(BloodRequest.id)).group_by(BloodRequest.status)}
    per_city = dict(db.query(BloodRequest.city, func.count(BloodRequest.id)).group_by(BloodRequest.city)
                    .order_by(func.count(BloodRequest.id).desc()).limit(10).all())

    since = utcnow() - timedelta(days=29)
    days = Counter(r.created_at.date().isoformat()
                   for r in db.query(BloodRequest.created_at).filter(BloodRequest.created_at >= since))
    requests_over_time = [{"date": (since + timedelta(days=i)).date().isoformat(),
                           "count": days.get((since + timedelta(days=i)).date().isoformat(), 0)} for i in range(30)]
    months = Counter(d.donation_date.strftime("%Y-%m") for d in db.query(Donation.donation_date))
    availability = dict(db.query(BloodInventory.blood_group, func.sum(BloodInventory.available_units))
                        .group_by(BloodInventory.blood_group).all())

    # Average minutes from request creation to first donor acceptance.
    accepted = db.query(BloodRequest.created_at, func.min(DonorMatch.responded_at)) \
        .join(DonorMatch, DonorMatch.request_id == BloodRequest.id) \
        .filter(DonorMatch.status.in_([MatchStatus.ACCEPTED, MatchStatus.CONFIRMED]),
                DonorMatch.responded_at.isnot(None)) \
        .group_by(BloodRequest.id, BloodRequest.created_at).all()
    waits = [(r - c).total_seconds() / 60 for c, r in accepted if r and c]
    return {
        "blood_group_distribution": bg,
        "blood_group_demand": demand,
        "inventory_availability": {k: int(v or 0) for k, v in availability.items()},
        "emergency_breakdown": emergency,
        "status_breakdown": status,
        "requests_per_city": per_city,
        "requests_over_time": requests_over_time,
        "donations_per_month": dict(sorted(months.items())),
        "average_minutes_to_first_acceptance": round(sum(waits) / len(waits), 1) if waits else None,
    }


@router.get("/users")
def users(search: Optional[str] = None, role: Optional[UserRole] = None,
          current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if search:
        q = q.filter(or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    return [{"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "role": u.role.value,
             "is_verified": u.is_verified, "is_blocked": u.is_blocked, "created_at": u.created_at.isoformat()}
            for u in q.order_by(User.created_at.desc()).all()]


@router.get("/donors")
def donors(current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    out = []
    for d in db.query(DonorProfile).all():
        eligible, reason = donor_eligibility(d)
        out.append({"id": d.id, "user_id": d.user_id, "name": d.user.name, "email": d.user.email,
                    "blood_group": d.blood_group, "city": d.city, "available": d.available,
                    "eligible": eligible, "eligibility_reason": reason, "total_donations": d.total_donations,
                    "is_blocked": d.user.is_blocked})
    return out


@router.get("/hospitals")
def hospitals(current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [{"id": h.id, "user_id": h.user_id, "name": h.name, "facility_type": h.facility_type.value,
             "city": h.city, "phone": h.phone, "email": h.email, "verified": h.verified,
             "inventory_rows": len(h.inventory)} for h in db.query(Hospital).all()]


@router.get("/requests")
def requests(current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [private_request(r) for r in db.query(BloodRequest).order_by(BloodRequest.created_at.desc()).all()]


@router.get("/audit-logs")
def audit_logs(limit: int = Query(100, ge=1, le=500), current_user: User = Depends(admin_only),
               db: Session = Depends(get_db)):
    return [{"id": a.id, "user_id": a.user_id, "action": a.action, "entity": a.entity, "entity_id": a.entity_id,
             "details": a.details, "ip_address": a.ip_address, "created_at": a.created_at.isoformat()}
            for a in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)]


@router.put("/users/{user_id}/verify")
def verify_user(user_id: int, request: Request, verified: bool = True,
                current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    user.is_verified = verified
    if user.hospital_profile:
        user.hospital_profile.verified = verified
    audit(db, current_user.id, "USER_VERIFIED" if verified else "USER_UNVERIFIED", "user", user.id, None, request)
    db.commit()
    return {"message": f"User #{user_id} verification set to {verified}."}


@router.put("/users/{user_id}/block")
def block_user(user_id: int, request: Request, blocked: bool = True,
               current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    if user.id == current_user.id:
        raise HTTPException(400, "You cannot block your own account.")
    user.is_blocked = blocked
    audit(db, current_user.id, "USER_BLOCKED" if blocked else "USER_UNBLOCKED", "user", user.id, None, request)
    db.commit()
    return {"message": f"User #{user_id} block status set to {blocked}."}


@router.put("/requests/{request_id}/flag-suspicious")
def flag_request(request_id: int, request: Request, is_suspicious: bool = True,
                 current_user: User = Depends(admin_only), db: Session = Depends(get_db)):
    req = db.get(BloodRequest, request_id)
    if not req:
        raise HTTPException(404, "Blood request not found.")
    req.is_suspicious = is_suspicious
    audit(db, current_user.id, "REQUEST_FLAGGED" if is_suspicious else "REQUEST_UNFLAGGED", "blood_request", req.id,
          None, request)
    db.commit()
    return {"message": f"Request #{request_id} suspicious status set to {is_suspicious}."}
