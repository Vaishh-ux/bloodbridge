from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.blood_request import EmergencyLevel
from app.schemas.common import check_lat_lng, clean_blood_group


class BloodRequestCreate(BaseModel):
    patient_name: Optional[str] = Field(default=None, max_length=150)
    blood_group: str
    units_required: int = Field(ge=1, le=20)
    emergency_level: EmergencyLevel
    hospital_id: Optional[int] = None  # pick a registered facility, or type details manually
    hospital_name: Optional[str] = Field(default=None, max_length=150)
    hospital_address: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    required_date: date
    required_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("blood_group")
    @classmethod
    def bg(cls, v):
        return clean_blood_group(v)

    @model_validator(mode="after")
    def checks(self):
        if self.required_date < date.today():
            raise ValueError("Required date cannot be in the past.")
        check_lat_lng(self.latitude, self.longitude)
        # Hospital details are checked in the route: a hospital account raising its own
        # request uses its registered profile, so it sends neither hospital_id nor details.
        return self


class BloodRequestUpdate(BaseModel):
    units_required: Optional[int] = Field(default=None, ge=1, le=20)
    emergency_level: Optional[EmergencyLevel] = None
    required_date: Optional[date] = None
    required_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    notes: Optional[str] = Field(default=None, max_length=1000)


class PublicRequestOut(BaseModel):
    """Safe public view: no patient name, notes or exact coordinates."""
    id: int
    blood_group: str
    units_required: int
    emergency_level: str
    hospital_id: Optional[int]
    hospital_name: str
    city: str
    state: str
    status: str
    required_date: str
    required_time: str
    approx_latitude: float
    approx_longitude: float
    created_at: datetime
