"""Helpers that decide what is safe to show publicly."""
from typing import Optional

from app.config import settings


def approx(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, settings.PUBLIC_LOCATION_DECIMALS)


def initials_name(full_name: Optional[str]) -> str:
    """'Arun Kumar' -> 'Arun K.'  (used before a donor has agreed to share details)."""
    if not full_name:
        return "Donor"
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


def public_request(req) -> dict:
    return {
        "id": req.id,
        "blood_group": req.blood_group,
        "units_required": req.units_required,
        "emergency_level": req.emergency_level.value,
        "hospital_id": req.hospital_id,
        "hospital_name": req.hospital_name,
        "city": req.city,
        "state": req.state,
        "status": req.status.value,
        "required_date": req.required_date,
        "required_time": req.required_time,
        "approx_latitude": approx(req.latitude),
        "approx_longitude": approx(req.longitude),
        "is_verified_facility": bool(req.hospital and req.hospital.verified),
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


def private_request(req) -> dict:
    data = public_request(req)
    data.update(
        {
            "patient_name": req.patient_name,
            "hospital_address": req.hospital_address,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "notes": req.notes,
            "is_suspicious": req.is_suspicious,
            "created_by_user_id": req.created_by_user_id,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        }
    )
    return data
