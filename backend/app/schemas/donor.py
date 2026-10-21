from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import check_lat_lng, clean_blood_group, clean_phone, clean_pincode, not_future


class DonorProfileUpdate(BaseModel):
    phone: Optional[str] = None
    blood_group: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=15)
    address: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    state: Optional[str] = Field(default=None, min_length=2, max_length=100)
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_donation_date: Optional[date] = None
    meets_basic_criteria: Optional[bool] = None

    @field_validator("blood_group")
    @classmethod
    def v_blood_group(cls, v):
        return clean_blood_group(v)

    @field_validator("pincode")
    @classmethod
    def v_pincode(cls, v):
        return clean_pincode(v)

    @field_validator("phone")
    @classmethod
    def phone_ok(cls, v):
        return clean_phone(v) if v else None

    @model_validator(mode="after")
    def checks(self):
        check_lat_lng(self.latitude, self.longitude)
        not_future(self.date_of_birth, "Date of birth")
        not_future(self.last_donation_date, "Last donation date")
        return self


class AvailabilityUpdate(BaseModel):
    available: bool
