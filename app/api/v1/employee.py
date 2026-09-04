"""
app/api/v1/employee.py
Employee-facing endpoints for managing reports within their governorate.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_employee, require_employee_or_admin  
from app.core.exceptions import PermissionDeniedError
from app.database import get_db  
from app.models.comment import ReportComment
from app.models.report import Report
from app.models.user import User, UserRole  
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.report import (
    ReportDetailResponse,
    ReportResponse,
    ResolveRequest,
    StatusUpdateRequest,
)
from app.services import report_service

router = APIRouter(prefix="/employee", tags=["Employee"])


@router.get("/reports", response_model=list[ReportResponse])
def list_governorate_reports(
    db: Session = Depends(get_db),
    employee: User = Depends(require_employee),
):
    """List all reports in the employee's governorate."""
    return (
        db.query(Report)
        .filter(Report.governorate_id == employee.governorate_id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.get("/reports/{report_id}/comments")
def get_employee_comments(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee_or_admin),
):
    """
    Get all comments (public + internal) for a report.
    Employee must belong to the same governorate.
    Admin can view any report's comments.
    """
    if current_user.role == UserRole.employee:
        report = db.get(Report, report_id)
        if not report or report.governorate_id != current_user.governorate_id:
            raise PermissionDeniedError("You can only view comments for reports in your governorate.")

    comments = (
        db.query(ReportComment)
        .filter(ReportComment.report_id == report_id)
        .order_by(ReportComment.created_at.asc())
        .all()
    )
    return comments


@router.patch("/reports/{report_id}/status", response_model=ReportResponse)
def update_status(
    report_id: int,
    data: StatusUpdateRequest,
    db: Session = Depends(get_db),
    employee: User = Depends(require_employee),
):
    """Update the status of a report in the employee's governorate."""
    return report_service.employee_update_status(db, employee, report_id, data)


@router.post("/reports/{report_id}/comments", response_model=CommentResponse, status_code=201)
def add_public_comment(
    report_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    employee: User = Depends(require_employee),
):
    """Add a public comment to a report (visible to the citizen)."""
    report_service.get_report_for_employee(db, employee, report_id)
    return report_service.add_comment(db, employee, report_id, data.content, is_internal=False)


@router.post("/reports/{report_id}/internal-notes", response_model=CommentResponse, status_code=201)
def add_internal_note(
    report_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_employee_or_admin),
):
    """
    Add an internal note (is_internal=True) to a report.
    Employee must belong to the same governorate.
    Admin can add internal notes to any report.
    """
    if current_user.role == UserRole.employee:
        report = db.get(Report, report_id)
        if not report or report.governorate_id != current_user.governorate_id:
            raise PermissionDeniedError("You can only add notes to reports in your governorate.")

    return report_service.add_comment(
        db=db,
        author=current_user,
        report_id=report_id,
        content=data.content,
        is_internal=True,
    )


@router.post("/reports/{report_id}/resolve", response_model=ReportResponse)
def resolve_report(
    report_id: int,
    data: ResolveRequest,
    db: Session = Depends(get_db),
    employee: User = Depends(require_employee),
):
    """Resolve a report with a mandatory resolution summary."""
    return report_service.employee_resolve_report(db, employee, report_id, data)