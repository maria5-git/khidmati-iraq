"""
app/api/v1/auth.py
Authentication endpoints: register, login, me.
Supports both JSON body and OAuth2 form-data for Swagger UI Authorize modal.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user
from app.core.exceptions import AuthenticationError
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserPublic, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new citizen account."""
    return auth_service.register_citizen(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Login and receive a JWT access token.
    Supports both JSON body ({"email": "...", "password": "..."})
    and OAuth2 form-data (username=...&password=...) for Swagger UI Authorize button.
    """
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")
    else:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            email = None
            password = None

    if not email or not password:
        raise AuthenticationError("Invalid email or password.")

    return auth_service.login_user(db, str(email), str(password))


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_active_user)):
    """Return the currently authenticated user's profile."""
    return UserPublic.model_validate(current_user)
