"""
app/services/auth_service.py
Business logic for registration and login.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError, InactiveUserError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserPublic


def register_citizen(db: Session, data: RegisterRequest) -> UserPublic:
    """
    Create a new citizen account.
    Raises ConflictError if the email is already taken.
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise ConflictError("An account with this email already exists.")

    user = User(
        full_name=data.full_name,
        email=data.email,
        phone_number=data.phone_number,
        hashed_password=hash_password(data.password),
        role=UserRole.citizen,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user)


def login_user(db: Session, email: str, password: str) -> TokenResponse:
    """
    Validate credentials and return a JWT token with basic user info.

    Raises:
        AuthenticationError – unknown email or wrong password.
        InactiveUserError – account is deactivated.
    """
    user = db.query(User).filter(User.email == email).first()

    # Use the same error message for both "not found" and "wrong password"
    # to avoid leaking information about which emails exist.
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise InactiveUserError()

    token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserPublic.model_validate(user),
    )
