"""
app/schemas/location.py
Pydantic v2 schemas for governorates and areas.
"""

from datetime import datetime

from pydantic import BaseModel


class GovernorateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name_ar: str
    name_en: str
    is_active: bool
    created_at: datetime


class AreaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    governorate_id: int
    name_ar: str
    name_en: str
    is_active: bool
    created_at: datetime
