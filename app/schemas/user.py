"""
app/schemas/user.py
Pydantic v2 schemas for user data.
Passwords are never included in response models.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserPublic(BaseModel):
    """Safe user data returned in API responses – no password field."""
    model_config = {"from_attributes": True}

    id: int
    full_name: str
    email: str
    phone_number: str | None
    role: UserRole
    governorate_id: int | None
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    """Used internally to create any user type."""
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    password: str
    role: UserRole = UserRole.citizen
    governorate_id: int | None = None


class CreateEmployeeRequest(BaseModel):
    """Admin creates an employee account."""
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    password: str
    governorate_id: int
