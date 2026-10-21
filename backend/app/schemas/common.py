import re
from datetime import date
from typing import Optional

from app.constants import BLOOD_GROUPS

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{6,18}$")
PINCODE_RE = re.compile(r"^[A-Za-z0-9\- ]{3,10}$")


def clean_blood_group(v: Optional[str]) -> Optional[str]:
    if v is None or v == "":
        return None
    v = v.strip().upper().replace(" ", "")
    if v not in BLOOD_GROUPS:
        raise ValueError(f"Blood group must be one of {', '.join(BLOOD_GROUPS)}.")
    return v


def clean_phone(v: str) -> str:
    v = v.strip()
    if not PHONE_RE.match(v):
        raise ValueError("Enter a valid phone number (digits, optional + country code).")
    return v


def clean_pincode(v: Optional[str]) -> Optional[str]:
    if v is None or v.strip() == "":
        return None
    v = v.strip()
    if not PINCODE_RE.match(v):
        raise ValueError("Enter a valid PIN / postal code.")
    return v


def check_lat_lng(lat: Optional[float], lng: Optional[float]) -> None:
    if (lat is None) != (lng is None):
        raise ValueError("Provide both latitude and longitude, or neither.")
    if lat is not None and not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Latitude/longitude are out of range.")
    if lat == 0 and lng == 0:
        raise ValueError("Location 0,0 is not a valid address. Please set your location.")


def not_future(v: Optional[date], label: str) -> Optional[date]:
    if v is not None and v > date.today():
        raise ValueError(f"{label} cannot be in the future.")
    return v
