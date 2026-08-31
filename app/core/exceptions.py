"""
app/core/exceptions.py
Custom application exceptions with consistent JSON error responses.
"""

from fastapi import HTTPException, status


def _make_detail(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# 404 – Not Found
# ---------------------------------------------------------------------------

class NotFoundError(HTTPException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_detail(
                f"{resource.upper().replace(' ', '_')}_NOT_FOUND",
                f"{resource} was not found.",
            ),
        )


# ---------------------------------------------------------------------------
# 403 – Forbidden
# ---------------------------------------------------------------------------

class PermissionDeniedError(HTTPException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_make_detail("PERMISSION_DENIED", message),
        )


# ---------------------------------------------------------------------------
# 409 – Conflict
# ---------------------------------------------------------------------------

class ConflictError(HTTPException):
    def __init__(self, message: str = "A conflict occurred."):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=_make_detail("CONFLICT", message),
        )


# ---------------------------------------------------------------------------
# 422 – Invalid status transition
# ---------------------------------------------------------------------------

class InvalidStatusTransitionError(HTTPException):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_make_detail(
                "INVALID_STATUS_TRANSITION",
                f"Cannot transition from '{from_status}' to '{to_status}'.",
            ),
        )


# ---------------------------------------------------------------------------
# 403 – Inactive user
# ---------------------------------------------------------------------------

class InactiveUserError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_make_detail(
                "INACTIVE_USER",
                "This account has been deactivated. Please contact support.",
            ),
        )


# ---------------------------------------------------------------------------
# 401 – Not authenticated
# ---------------------------------------------------------------------------

class AuthenticationError(HTTPException):
    def __init__(self, message: str = "Invalid credentials."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_make_detail("AUTHENTICATION_FAILED", message),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# 400 – Validation / business rule
# ---------------------------------------------------------------------------

class BadRequestError(HTTPException):
    def __init__(self, code: str, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_detail(code, message),
        )
