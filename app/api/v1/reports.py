"""
app/api/v1/reports.py
Citizen-facing report endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_citizen
from app.database import get_db
from app.models.comment import ReportComment
from app.models.report import Report
from app.models.status_history import ReportStatusHistory
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.report import (
    ReportCreate,
    ReportDetailResponse,  # استخدمنا هذا لأنه موجود في الملف
    ReportResponse,        # أضفناه للاستيراد
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
    citizen: User = Depends(require_citizen),  # تم التعديل هنا
):
    """
    Get a specific report. 
    Only the citizen who owns the report can view it.
    """
    # استخدم الدالة التي تتحقق من الملكية (سنضيفها في الـ service)
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
    # 1. تحقق من أن المواطن يملك البلاغ
    report = report_service.get_citizen_report_or_404(db, id, citizen.id)
    
    # 2. قم بتحديث البلاغ (نمرر citizen.id للتأكد في الـ Service أيضاً)
    updated_report = report_service.update_report(db, id, report_update, citizen.id)
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
    # 1. تحقق من الملكية
    report = report_service.get_citizen_report_or_404(db, id, citizen.id)
    
    # 2. قم بالإلغاء (نمرر citizen.id للتأكد)
    cancelled_report = report_service.cancel_report(db, id, citizen.id)
    return cancelled_report


# ----------------------------------------------
# 6. عرض سجل التحديثات (مع التحقق من الملكية)
# ----------------------------------------------
@router.get("/{report_id}/history", response_model=list[StatusHistoryResponse])
def get_report_history(
    report_id: int,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_citizen),
):
    """Return the status-change history for the citizen's report."""
    # تأكد من أن المواطن يملك البلاغ أولاً
    report_service.get_citizen_report_or_404(db, report_id, citizen.id)
    
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
    # تأكد من الملكية
    report_service.get_citizen_report_or_404(db, id, citizen.id)
    
    # جلب التعليقات العامة فقط (is_internal=False)
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
    # تأكد من الملكية قبل التعليق
    report_service.get_citizen_report_or_404(db, report_id, citizen.id)
    
    # أضف التعليق (is_internal=False لأن مواطن لا يكتب داخلياً)
    return report_service.add_comment(db, citizen, report_id, data.content, is_internal=False)