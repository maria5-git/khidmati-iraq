"""
app/schemas/category.py
Pydantic v2 schema for ServiceCategory.
"""

from datetime import datetime

from pydantic import BaseModel


class CategoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name_ar: str
    name_en: str
    description: str | None
    is_active: bool
    created_at: datetime
