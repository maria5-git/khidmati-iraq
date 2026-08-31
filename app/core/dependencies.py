"""
app/core/dependencies.py
Reusable FastAPI dependencies for authentication and role enforcement.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, InactiveUserError, PermissionDeniedError
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User, UserRole

# OAuth2 scheme – FastAPI will look for the token in the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the JWT token and return the corresponding User.
    Raises 401 if the token is invalid or the user does not exist.
    """
    user_id = decode_access_token(token)
    if user_id is None:
        raise AuthenticationError("Invalid or expired token.")

    user = db.get(User, int(user_id))
    if user is None:
        raise AuthenticationError("User not found.")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Reject requests from inactive users."""
    if not current_user.is_active:
        raise InactiveUserError()
    return current_user


def require_citizen(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Allow citizens only."""
    if current_user.role != UserRole.citizen:
        raise PermissionDeniedError("Citizens only.")
    return current_user


def require_employee(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Allow employees only."""
    if current_user.role != UserRole.employee:
        raise PermissionDeniedError("Employees only.")
    return current_user


def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Allow admins only."""
    if current_user.role != UserRole.admin:
        raise PermissionDeniedError("Admins only.")
    return current_user


def require_employee_or_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Allow employees and admins."""
    if current_user.role not in (UserRole.employee, UserRole.admin):
        raise PermissionDeniedError("Employees or admins only.")
    return current_user
