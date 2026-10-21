from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.hospital import FacilityType
from app.models.user import UserRole
from app.schemas.common import check_lat_lng, clean_blood_group, clean_phone, clean_pincode, not_future


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.DONOR

    blood_group: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=15)
    address: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Donor-only
    available: bool = True
    last_donation_date: Optional[date] = None
    meets_basic_criteria: bool = False

    # Hospital-only
    facility_type: FacilityType = FacilityType.HOSPITAL

    @field_validator("blood_group")
    @classmethod
    def v_blood_group(cls, v):
        return clean_blood_group(v)

    @field_validator("phone")
    @classmethod
    def v_phone(cls, v):
        return clean_phone(v)

    @field_validator("pincode")
    @classmethod
    def v_pincode(cls, v):
        return clean_pincode(v)

    @field_validator("name", "city", "state")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("This field is required.")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long (maximum 72 bytes).")
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number.")
        return v

    @model_validator(mode="after")
    def role_rules(self):
        if self.role == UserRole.ADMIN:
            raise ValueError("Administrator accounts cannot be created through public registration.")
        check_lat_lng(self.latitude, self.longitude)
        not_future(self.date_of_birth, "Date of birth")
        not_future(self.last_donation_date, "Last donation date")
        if self.role == UserRole.DONOR:
            if not self.blood_group:
                raise ValueError("Blood group is required for donors.")
        if self.role == UserRole.HOSPITAL:
            if not self.address or len(self.address.strip()) < 5:
                raise ValueError("Facility address is required.")
            if self.latitude is None:
                raise ValueError("Facility location is required so it can appear on the map. Use 'Locate' or enter coordinates.")
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    role: Optional[UserRole] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    email: str
    role: UserRole
