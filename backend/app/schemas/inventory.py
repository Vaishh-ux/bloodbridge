from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.inventory import BloodComponent
from app.schemas.common import clean_blood_group


class BloodInventoryUpdate(BaseModel):
    blood_group: str
    component: BloodComponent = BloodComponent.WHOLE_BLOOD
    available_units: int = Field(ge=0, le=100000)
    reserved_units: int = Field(default=0, ge=0, le=100000)
    reason: Optional[str] = Field(default=None, max_length=255)

    @field_validator("blood_group")
    @classmethod
    def bg(cls, v):
        return clean_blood_group(v)


# Backwards-compatible name used by the original code.
BloodInventoryCreate = BloodInventoryUpdate


class BloodInventoryResponse(BaseModel):
    id: int
    hospital_id: int
    blood_group: str
    component: str
    available_units: int
    reserved_units: int
    last_updated: datetime

    model_config = {"from_attributes": True}
