"""
app/api/v1/reports.py
Citizen-facing report endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_citizen  
from app.database import get_db
from app.models.comment import ReportComment
from app.models.report import Report
from app.models.status_history import ReportStatusHistory
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.report import (
    ReportCreate,
    ReportDetailResponse,
    ReportResponse,
    ReportUpdate,
    StatusHistoryResponse,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports – Citizen"])

# ----------------------------------------------
# 1. إنشاء بلاغ جديد (مواطن فقط)
# ----------------------------------------------
@router.post("", response_model=ReportResponse, status_code=201)
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """Submit a new service-problem report."""
    return report_service.create_report(db, citizen, data)

# ----------------------------------------------
# 2. عرض بلاغاتي (قائمة)
# ----------------------------------------------
@router.get("/my", response_model=list[ReportResponse])
def my_reports(
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """List all reports submitted by the current citizen."""
    return (
        db.query(Report)
        .filter(Report.citizen_id == citizen.id)
        .order_by(Report.created_at.desc())
        .all()
    )

# ----------------------------------------------
# 3. عرض بلاغ معين (مع التحقق من الملكية)
# ----------------------------------------------
@router.get("/{id}", response_model=ReportDetailResponse)
def get_report(
    id: int,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """
    Get a specific report.
    Only the citizen who owns the report can view it.
    """
    report = report_service.get_citizen_report_or_404(db, id, citizen.id)
    return report

# ----------------------------------------------
# 4. تحديث بلاغ (مع التحقق من الملكية)
# ----------------------------------------------
@router.patch("/{id}", response_model=ReportDetailResponse)
def update_report(
    id: int,
    report_update: ReportUpdate,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """
    Update a report.
    Only the owner can update it.
    """
    # استخدم الدالة الصحيحة (update_citizen_report) مع ترتيب المعاملات الصحيح
    updated_report = report_service.update_citizen_report(db, citizen, id, report_update)
    return updated_report

# ----------------------------------------------
# 5. إلغاء بلاغ (مع التحقق من الملكية)
# ----------------------------------------------
@router.post("/{id}/cancel")
def cancel_report(
    id: int,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """
    Cancel a report.
    Only the owner can cancel it.
    """
    cancelled_report = report_service.cancel_report(db, citizen, id)
    return cancelled_report

# ----------------------------------------------
# 6. عرض سجل التحديثات (مع صلاحيات متعددة)
# ----------------------------------------------
@router.get("/{report_id}/history", response_model=list[StatusHistoryResponse])
def get_report_history(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user), 
):
    """
    Return the status-change history for the report.
    Allowed access:
    - The citizen who owns the report.
    - An employee belonging to the same governorate.
    - Any admin.
    """
    from app.core.exceptions import NotFoundError, PermissionDeniedError

    report = db.get(Report, report_id)
    if not report:
        raise NotFoundError("Report")

    is_owner = (report.citizen_id == current_user.id)
    is_employee_in_governorate = (
        current_user.role == UserRole.employee and
        report.governorate_id == current_user.governorate_id
    )
    is_admin = (current_user.role == UserRole.admin)

    if not (is_owner or is_employee_in_governorate or is_admin):
        raise PermissionDeniedError(
            "You do not have permission to view this report's history."
        )

    return (
        db.query(ReportStatusHistory)
        .filter(ReportStatusHistory.report_id == report_id)
        .order_by(ReportStatusHistory.created_at.asc())
        .all()
    )

# ----------------------------------------------
# 7. عرض التعليقات العامة (مع التحقق من الملكية)
# ----------------------------------------------
@router.get("/{id}/comments")
def get_comments(
    id: int,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """Get public comments for the citizen's own report."""
    report_service.get_citizen_report_or_404(db, id, citizen.id)

    comments = (
        db.query(ReportComment)
        .filter(ReportComment.report_id == id, ReportComment.is_internal == False)
        .order_by(ReportComment.created_at.asc())
        .all()
    )
    return comments

# ----------------------------------------------
# 8. إضافة تعليق عام (مع التحقق من الملكية)
# ----------------------------------------------
@router.post("/{report_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(
    report_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """Add a public comment to the citizen's own report."""
    report_service.get_citizen_report_or_404(db, report_id, citizen.id)
    return report_service.add_comment(db, citizen, report_id, data.content, is_internal=False)