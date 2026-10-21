from app.timeutil import utcnow
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user, require_roles
from app.constants import BLOOD_GROUPS
from app.database import get_db
from app.models.blood_request import BloodRequest, RequestStatus
from app.models.hospital import FacilityType, Hospital
from app.models.inventory import (COMPONENT_LABELS, RED_CELL_COMPONENTS, BloodComponent, BloodInventory,
                                  InventoryLog)
from app.models.match import MatchStatus
from app.models.user import User, UserRole
from app.routers.requests import notify_request_parties
from app.schemas.common import check_lat_lng, clean_phone, clean_pincode
from app.schemas.inventory import BloodInventoryUpdate
from app.services.audit import audit
from app.services.distance_service import calculate_haversine_distance
from app.services.matching_service import compatible_donor_groups
from app.services.privacy import private_request

router = APIRouter(prefix="/hospitals", tags=["Hospitals & Inventory"])

LOW_STOCK_UNITS = 5


def _hospital_or_404(db: Session, hospital_id: int) -> Hospital:
    h = db.get(Hospital, hospital_id)
    if not h:
        raise HTTPException(404, "Hospital not found.")
    return h


def _ensure_staff(user: User, hospital: Hospital) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.HOSPITAL and user.hospital_profile and user.hospital_profile.id == hospital.id:
        return
    raise HTTPException(403, "Only this facility's account can manage its data.")


COMPONENT_ORDER = [c.value for c in BloodComponent]


def _inventory_rows(h: Hospital):
    rows = sorted(h.inventory, key=lambda r: (COMPONENT_ORDER.index(r.component) if r.component in COMPONENT_ORDER else 99,
                                              BLOOD_GROUPS.index(r.blood_group)))
    return [{"id": i.id, "hospital_id": i.hospital_id, "blood_group": i.blood_group,
             "component": i.component, "component_label": COMPONENT_LABELS.get(BloodComponent(i.component), i.component),
             "available_units": i.available_units, "reserved_units": i.reserved_units,
             "status": "OUT" if i.available_units == 0 else ("LOW" if i.available_units < LOW_STOCK_UNITS else "OK"),
             "last_updated": i.last_updated.isoformat() if i.last_updated else None}
            for i in rows]


def _is_staff(user: Optional[User], h: Hospital) -> bool:
    return bool(user and (user.role == UserRole.ADMIN or (user.role == UserRole.HOSPITAL and user.hospital_profile
                                                            and user.hospital_profile.id == h.id)))


def _public_hospital(h: Hospital, dist: Optional[float] = None, show_stock: Optional[bool] = None) -> dict:
    """Stock is published only for facilities an administrator has verified (staff always see their own)."""
    if show_stock is None:
        show_stock = h.verified
    inv = _inventory_rows(h)
    visible = inv if show_stock else []
    return {
        "id": h.id, "name": h.name, "facility_type": h.facility_type.value, "email": h.email, "phone": h.phone,
        "address": h.address, "city": h.city, "state": h.state, "pincode": h.pincode,
        "latitude": h.latitude, "longitude": h.longitude, "verified": h.verified,
        "distance_km": round(dist, 1) if dist is not None else None,
        "inventory_reported": bool(visible),
        "stock_hidden_until_verified": bool(inv) and not show_stock,
        "inventory_last_updated": max((r["last_updated"] for r in visible), default=None),
        "inventory": visible,
    }


@router.get("")
def list_hospitals(
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    facility_type: Optional[FacilityType] = None,
    blood_group: Optional[str] = Query(None, description="Only facilities reporting stock usable for this recipient"),
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = Query(None, gt=0, le=2000),
    db: Session = Depends(get_db),
):
    """Registered hospitals and blood banks, with the stock they have reported (if any)."""
    q = db.query(Hospital).join(User, User.id == Hospital.user_id).filter(User.is_blocked.is_(False))
    if city:
        q = q.filter(Hospital.city.ilike(f"%{city.strip()}%"))
    if pincode:
        q = q.filter(Hospital.pincode.ilike(f"{pincode.strip()}%"))
    if facility_type:
        q = q.filter(Hospital.facility_type == facility_type)
    out = []
    for h in q.all():
        dist = None
        if lat is not None and lng is not None and h.latitude is not None:
            dist = calculate_haversine_distance(lat, lng, h.latitude, h.longitude)
            if radius_km and dist > radius_km:
                continue
        item = _public_hospital(h, dist)
        if blood_group:
            groups = compatible_donor_groups(blood_group.upper())
            if not any(r["blood_group"] in groups and r["component"] in RED_CELL_COMPONENTS and r["available_units"] > 0
                       for r in item["inventory"]):
                continue
        out.append(item)
    out.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 0, not x["verified"], x["name"]))
    return out


@router.get("/me")
def my_facility(current_user: User = Depends(require_roles([UserRole.HOSPITAL])), db: Session = Depends(get_db)):
    h = current_user.hospital_profile
    if not h:
        raise HTTPException(404, "Facility profile not found.")
    return _public_hospital(h, show_stock=True)


class HospitalUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    facility_type: Optional[FacilityType] = None
    phone: Optional[str] = None
    address: Optional[str] = Field(default=None, min_length=5, max_length=255)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    state: Optional[str] = Field(default=None, min_length=2, max_length=100)
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @model_validator(mode="after")
    def checks(self):
        if self.phone:
            self.phone = clean_phone(self.phone)
        self.pincode = clean_pincode(self.pincode)
        check_lat_lng(self.latitude, self.longitude)
        return self


@router.put("/me")
def update_my_facility(payload: HospitalUpdate, current_user: User = Depends(require_roles([UserRole.HOSPITAL])),
                       db: Session = Depends(get_db)):
    h = current_user.hospital_profile
    if not h:
        raise HTTPException(404, "Facility profile not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(h, k, v)
    db.commit()
    return _public_hospital(h, show_stock=True)


@router.get("/{hospital_id}")
def get_hospital(hospital_id: int, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    h = _hospital_or_404(db, hospital_id)
    return _public_hospital(h, show_stock=h.verified or _is_staff(user, h))


@router.get("/{hospital_id}/inventory")
def get_hospital_inventory(hospital_id: int, db: Session = Depends(get_db),
                           user: Optional[User] = Depends(get_optional_user)):
    """Stock exactly as reported by the facility (never auto-filled).

    The public sees it only once the facility is verified; the facility and admins always see it.
    """
    h = _hospital_or_404(db, hospital_id)
    if not (h.verified or _is_staff(user, h)):
        return []
    return _inventory_rows(h)


def _apply_inventory(db: Session, h: Hospital, item: BloodInventoryUpdate, user: User, request: Request):
    comp = item.component.value
    inv = db.query(BloodInventory).filter(BloodInventory.hospital_id == h.id,
                                          BloodInventory.blood_group == item.blood_group,
                                          BloodInventory.component == comp).first()
    before_a, before_r = (inv.available_units, inv.reserved_units) if inv else (0, 0)
    if not inv:
        inv = BloodInventory(hospital_id=h.id, blood_group=item.blood_group, component=comp)
        db.add(inv)
    inv.available_units = item.available_units
    inv.reserved_units = item.reserved_units
    inv.updated_by_user_id = user.id
    inv.last_updated = utcnow()
    db.add(InventoryLog(hospital_id=h.id, blood_group=item.blood_group, component=comp,
                        available_change=item.available_units - before_a, reserved_change=item.reserved_units - before_r,
                        available_after=item.available_units, reserved_after=item.reserved_units,
                        reason=(item.reason or "Stock update").strip(), user_id=user.id))
    audit(db, user.id, "INVENTORY_UPDATED", "hospital", h.id, f"{item.blood_group} {comp}: {before_a}->{item.available_units}",
          request)
    return inv


@router.post("/{hospital_id}/inventory")
@router.put("/{hospital_id}/inventory")
def update_hospital_inventory(hospital_id: int, item: BloodInventoryUpdate, request: Request,
                              current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = _hospital_or_404(db, hospital_id)
    _ensure_staff(current_user, h)
    _apply_inventory(db, h, item, current_user, request)
    db.commit()
    db.refresh(h)
    return _inventory_rows(h)


@router.get("/{hospital_id}/inventory/history")
def inventory_history(hospital_id: int, limit: int = Query(100, ge=1, le=500),
                      current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = _hospital_or_404(db, hospital_id)
    _ensure_staff(current_user, h)
    rows = db.query(InventoryLog).filter(InventoryLog.hospital_id == h.id) \
        .order_by(InventoryLog.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "blood_group": r.blood_group,
             "component": r.component or BloodComponent.WHOLE_BLOOD.value,
             "component_label": COMPONENT_LABELS.get(BloodComponent(r.component or "WHOLE_BLOOD")),
             "available_change": r.available_change,
             "reserved_change": r.reserved_change, "available_after": r.available_after,
             "reserved_after": r.reserved_after, "reason": r.reason, "created_at": r.created_at.isoformat()}
            for r in rows]


@router.get("/{hospital_id}/requests")
def get_hospital_requests(hospital_id: int, current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    h = _hospital_or_404(db, hospital_id)
    _ensure_staff(current_user, h)
    reqs = db.query(BloodRequest).filter(BloodRequest.hospital_id == h.id) \
        .order_by(BloodRequest.created_at.desc()).all()
    out = []
    for r in reqs:
        item = private_request(r)
        item["units_fulfilled"] = sum(d.units for d in r.donations)
        item["accepted_matches"] = [
            {"match_id": m.id, "donor_name": m.donor.user.name, "donor_phone": m.donor.user.phone,
             "donor_blood_group": m.donor.blood_group, "status": m.status.value}
            for m in r.matches if m.status in (MatchStatus.ACCEPTED, MatchStatus.CONFIRMED)
        ]
        item["pending_matches"] = sum(1 for m in r.matches if m.status == MatchStatus.PENDING)
        out.append(item)
    return out


class FulfillFromStock(BaseModel):
    units: int = Field(ge=1, le=20)
    blood_group: Optional[str] = None  # defaults to the requested group
    component: BloodComponent = BloodComponent.WHOLE_BLOOD


@router.post("/{hospital_id}/requests/{request_id}/fulfill-from-stock")
async def fulfill_from_stock(hospital_id: int, request_id: int, body: FulfillFromStock, request: Request,
                             current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Issue units from this facility's own stock against a request and deduct inventory."""
    h = _hospital_or_404(db, hospital_id)
    _ensure_staff(current_user, h)
    req = db.get(BloodRequest, request_id)
    if not req or req.hospital_id != h.id:
        raise HTTPException(404, "Request not found for this facility.")
    if not req.is_active:
        raise HTTPException(400, "This request is no longer active.")
    group = (body.blood_group or req.blood_group).upper()
    if group not in compatible_donor_groups(req.blood_group):
        raise HTTPException(400, f"{group} is not red-cell compatible with a {req.blood_group} recipient.")
    if body.component.value not in RED_CELL_COMPONENTS:
        raise HTTPException(400, "Blood requests are for red cells: issue Whole Blood or Packed Red Cells.")
    label = COMPONENT_LABELS[body.component]
    inv = db.query(BloodInventory).filter(BloodInventory.hospital_id == h.id, BloodInventory.blood_group == group,
                                          BloodInventory.component == body.component.value).first()
    if not inv or inv.available_units < body.units:
        raise HTTPException(400, f"Not enough {group} {label} units in stock.")
    _apply_inventory(db, h, BloodInventoryUpdate(blood_group=group, component=body.component,
                                                 available_units=inv.available_units - body.units,
                                                 reserved_units=inv.reserved_units,
                                                 reason=f"Issued {body.units} unit(s) of {label} for request #{req.id}"),
                     current_user, request)
    req.status = RequestStatus.COMPLETED
    req.completed_at = utcnow()
    for m in req.matches:
        if m.status == MatchStatus.PENDING:
            m.status = MatchStatus.CLOSED
    db.commit()
    await notify_request_parties(db, req, "✅ Request Fulfilled From Hospital Stock",
                                 f"{body.units} unit(s) of {group} {label} were issued for request #{req.id}.",
                                 "REQUEST_COMPLETED", exclude_user_id=current_user.id)
    return {"message": "Units issued and inventory updated.", "request_status": req.status.value}
