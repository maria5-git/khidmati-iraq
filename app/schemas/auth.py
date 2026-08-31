"""
app/schemas/auth.py
Pydantic v2 schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserPublic


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    password: str


class LoginRequest(BaseModel):
    # Use plain str here so any stored email (including .local/.test domains)
    # can be used to log in. Registration still enforces proper EmailStr format.
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
