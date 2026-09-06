"""
app/services/report_service.py
Core business logic for report management.
All status-transition rules live in this file.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    InvalidStatusTransitionError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.area import Area
from app.models.category import ServiceCategory
from app.models.comment import ReportComment
from app.models.governorate import Governorate
from app.models.report import Report, ReportPriority, ReportStatus, generate_reference_number
from app.models.status_history import ReportStatusHistory
from app.models.user import User, UserRole
from app.schemas.report import (
    AssignRequest,
    PriorityUpdateRequest,
    ReportCreate,
    ReportUpdate,
    ResolveRequest,
    StatusUpdateRequest,
    ReportFilterParams,
)

# ---------------------------------------------------------------------------
# Valid status transitions
# ---------------------------------------------------------------------------

# Allowed transitions for employees
# جدول الانتقالات الصحيح (جميع الأدوار)
TRANSITIONS: dict[ReportStatus, list[ReportStatus]] = {
    ReportStatus.submitted: [ReportStatus.under_review, ReportStatus.rejected, ReportStatus.cancelled, ReportStatus.assigned,],
    ReportStatus.under_review: [ReportStatus.assigned, ReportStatus.rejected],
    ReportStatus.assigned: [ReportStatus.in_progress, ReportStatus.under_review],
    ReportStatus.in_progress: [ReportStatus.resolved, ReportStatus.assigned],
    # الحالات النهائية لا يمكن الانتقال منها لأي حالة أخرى
    ReportStatus.resolved: [],
    ReportStatus.rejected: [],
    ReportStatus.cancelled: [],
}
def validate_transition(from_status: ReportStatus, to_status: ReportStatus) -> None:
    allowed = TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        #  تمرير الوسيطين المطلوبين بشكل منفصل
        raise InvalidStatusTransitionError(from_status.value, to_status.value)


# ---------------------------------------------------------------------------
# Helper: record a status change in history
# ---------------------------------------------------------------------------

def record_status_change(
    db: Session,
    report: Report,
    new_status: ReportStatus,
    changed_by: User,
    note: str | None = None,
) -> None:
    """
    Update report.status and append a ReportStatusHistory row.
    Does NOT commit – the caller is responsible for the transaction.
    """
    history = ReportStatusHistory(
        report_id=report.id,
        previous_status=report.status.value if report.status else None,  
        new_status=new_status.value,  
        changed_by_id=changed_by.id,
        note=note,
    )
    report.status = new_status
    db.add(history)


# ---------------------------------------------------------------------------
# Helper: validate location consistency
# ---------------------------------------------------------------------------

def validate_location(
    db: Session,
    governorate_id: int,
    area_id: int,
    category_id: int,
) -> tuple[Governorate, Area, ServiceCategory]:
    """
    Ensure the governorate, area, and category exist, are active,
    and that the area belongs to the governorate.
    """
    governorate = db.get(Governorate, governorate_id)
    if not governorate or not governorate.is_active:
        raise BadRequestError("INVALID_GOVERNORATE", "Governorate not found or inactive.")

    area = db.get(Area, area_id)
    if not area or not area.is_active:
        raise BadRequestError("INVALID_AREA", "Area not found or inactive.")

    #  التحقق من أن المنطقة تنتمي إلى المحافظة المختارة
    if area.governorate_id != governorate_id:
        raise BadRequestError(
            "AREA_GOVERNORATE_MISMATCH",
            "Area does not belong to the selected governorate."
        )

    category = db.get(ServiceCategory, category_id)
    if not category or not category.is_active:
        raise BadRequestError("INVALID_CATEGORY", "Category not found or inactive.")

    return governorate, area, category


# ---------------------------------------------------------------------------
# Citizen actions
# ---------------------------------------------------------------------------

def create_report(db: Session, citizen: User, data: ReportCreate) -> Report:
    """Create a new report submitted by a citizen."""
    validate_location(db, data.governorate_id, data.area_id, data.category_id)

    year = datetime.now(timezone.utc).year
    ref = generate_reference_number(db, year)

    report = Report(
        reference_number=ref,
        citizen_id=citizen.id,
        category_id=data.category_id,
        governorate_id=data.governorate_id,
        area_id=data.area_id,
        title=data.title,
        description=data.description,
        address_details=data.address_details,
        status=ReportStatus.submitted,
        priority=ReportPriority.medium,
    )
    db.add(report)
    db.flush()      # تسجيل الحالة الأولية في سجل التاريخ
    record_status_change(
        db,
        report=report,
        new_status=ReportStatus.submitted,
        changed_by=citizen,
        note="Citizen submitted the report.",
    )
    db.commit()
    db.refresh(report)
    return report


def get_citizen_report_or_404(db: Session, report_id: int, citizen_id: int):
    """
    Retrieve a report only if it exists and belongs to the given citizen.
    Raises 404 Not Found otherwise (to avoid leaking existence of other reports).
    """
    from fastapi import HTTPException, status
    
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.citizen_id != citizen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    return report


def update_citizen_report(db: Session, citizen: User, report_id: int, data: ReportUpdate) -> Report:
    """
    Citizens can update a report only while it is in 'submitted' status.
    They cannot change status, priority, or assigned employee.
    """
    report = get_citizen_report_or_404(db, report_id, citizen.id)

    if report.status != ReportStatus.submitted:
        raise BadRequestError(
            "REPORT_NOT_EDITABLE",
            "You can only edit a report while it is in 'submitted' status.",
        )

    if data.category_id is not None or data.area_id is not None:
        # Re-validate location if either location field changed.
        new_cat = data.category_id if data.category_id else report.category_id
        new_area = data.area_id if data.area_id else report.area_id
        validate_location(db, report.governorate_id, new_area, new_cat)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)

    db.commit()
    db.refresh(report)
    return report


def cancel_report(db: Session, citizen: User, report_id: int) -> Report:
    """
    A citizen can cancel their own report only when it is in a cancellable state.
    Creates a status-history entry.
    """
    report = get_citizen_report_or_404(db, report_id, citizen.id)

    # استخدام دالة التحقق المركزية 
    validate_transition(report.status, ReportStatus.cancelled)

    # تسجيل التغيير في التاريخ
    record_status_change(
        db,
        report=report,
        new_status=ReportStatus.cancelled,
        changed_by=citizen,
        note="Citizen cancelled the report.",
    )

    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Employee actions
# ---------------------------------------------------------------------------

def get_report_for_employee(db: Session, employee: User, report_id: int) -> Report:
    """Return a report only if it belongs to the employee's governorate."""
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report")
    # Employees can only access reports from their governorate.
    if report.governorate_id != employee.governorate_id:
        raise PermissionDeniedError("This report is outside your governorate.")
    return report


def employee_update_status(
    db: Session, employee: User, report_id: int, data: StatusUpdateRequest
) -> Report:
    """Employee changes a report status."""
    report = get_report_for_employee(db, employee, report_id)
    
    # التحقق من أن الانتقال مسموح به 
    validate_transition(report.status, data.new_status)
    
    # تحديث الحالة وتسجيل التاريخ
    record_status_change(
        db,
        report=report,
        new_status=data.new_status,
        changed_by=employee,
        note=data.note if data.note else f"Status changed to {data.new_status.value}",
    )
    
    db.commit()
    db.refresh(report)
    return report


def employee_resolve_report(
    db: Session, employee: User, report_id: int, data: ResolveRequest
) -> Report:
    """
    Resolve a report.
    TASK-07: Enforce mandatory resolution summary and proper history tracking.
    """
    # 1. التأكد من أن الموظف لديه صلاحية على هذا البلاغ (نفس المحافظة)
    report = get_report_for_employee(db, employee, report_id)

    # 2. التحقق من أن ملخص الحل مطلوب وغير فارغ
    if not data.resolution_summary or not data.resolution_summary.strip():
        raise BadRequestError(
            "RESOLUTION_REQUIRED",
            "Resolution summary is required and cannot be empty or whitespace only."
        )

    # 3. التحقق من أن انتقال الحالة إلى 'resolved' مسموح به
    #    هذه الدالة سترفع InvalidStatusTransitionError إذا كان الانتقال غير مسموح،
    #    وسيتعامل معها FastAPI مباشرة (بدون تغليف منا)
    validate_transition(report.status, ReportStatus.resolved)

    # 4. تحديث بيانات البلاغ
    report.resolution_summary = data.resolution_summary.strip()
    report.resolved_at = datetime.now(timezone.utc)

    # 5. تسجيل التغيير في سجل التاريخ
    record_status_change(
        db,
        report=report,
        new_status=ReportStatus.resolved,
        changed_by=employee,
        note=f"Report resolved. Summary: {data.resolution_summary[:50]}..."
    )

    # 6. حفظ جميع التغييرات في قاعدة البيانات (دفعة واحدة)
    db.commit()
    db.refresh(report)
    return report


def add_comment(
    db: Session,
    author: User,
    report_id: int,
    content: str,
    is_internal: bool = False,
) -> ReportComment:
    """Add a comment to a report. is_internal is only allowed for staff."""
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report")

    comment = ReportComment(
        report_id=report_id,
        author_id=author.id,
        content=content,
        is_internal=is_internal,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


# ---------------------------------------------------------------------------
# Admin actions
# ---------------------------------------------------------------------------

def admin_assign_report(
    db: Session, admin: User, report_id: int, data: AssignRequest
) -> Report:
    """
    Admin assigns an employee to a report.
    Validates that the employee is active, an employee, and in the same governorate.
    """
    # 1. التحقق من وجود البلاغ
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report")

    # 2. التحقق من وجود الموظف
    employee = db.get(User, data.employee_id)
    if employee is None:
        raise NotFoundError("Employee")

    # 3. التحقق من أن المستخدم هو موظف فعلاً
    if employee.role != UserRole.employee:
        raise BadRequestError("NOT_EMPLOYEE", "The selected user is not an employee.")

    # 4. التحقق من أن الموظف نشط
    if not employee.is_active:
        raise BadRequestError("INACTIVE_EMPLOYEE", "The selected employee is inactive.")

    #  التحقق من أن الموظف يتبع نفس محافظة البلاغ
    if employee.governorate_id != report.governorate_id:
        raise BadRequestError(
            "EMPLOYEE_GOVERNORATE_MISMATCH",
            "Employee does not belong to the same governorate as the report."
        )

       # 5. تحديث بيانات البلاغ (التعيين وتغيير الحالة)
    report.assigned_employee_id = employee.id
    # التحقق من أن الانتقال إلى حالة 'assigned' مسموح به 
    validate_transition(report.status, ReportStatus.assigned)

    # تحديث الحالة وتسجيل التاريخ (مرة واحدة فقط)
    record_status_change(
        db,
        report=report,
        new_status=ReportStatus.assigned,
        changed_by=admin,
        note=data.note if data.note else f"Assigned to {employee.full_name}",
    )

    # 6. حفظ جميع التغييرات في قاعدة البيانات (دفعة واحدة)
    db.commit()
    db.refresh(report)
    return report


def admin_update_priority(
    db: Session, report_id: int, data: PriorityUpdateRequest
) -> Report:
    """Admin updates the priority of a report."""
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report")

    report.priority = data.priority
    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------

def get_dashboard_stats(db: Session) -> dict:
    """
    TASK-08: Return aggregated statistics for the admin dashboard.
    """
    from sqlalchemy import func

    # 1. إجمالي البلاغات
    total_reports = db.query(func.count(Report.id)).scalar() or 0

    # 2. البلاغات المفتوحة (ليست منتهية)
    open_statuses = [ReportStatus.submitted, ReportStatus.under_review, 
                     ReportStatus.assigned, ReportStatus.in_progress]
    open_reports = (
        db.query(func.count(Report.id))
        .filter(Report.status.in_(open_statuses))
        .scalar() or 0
    )

    # 3. البلاغات المغلقة (محلولة)
    resolved_reports = (
        db.query(func.count(Report.id))
        .filter(Report.status == ReportStatus.resolved)
        .scalar() or 0
    )

    # 4. التوزيع حسب الحالة
    status_breakdown = {}
    for status in ReportStatus:
        count = (
            db.query(func.count(Report.id))
            .filter(Report.status == status)
            .scalar() or 0
        )
        if count > 0:
            status_breakdown[status.value] = count

    # 5. التوزيع حسب الأولوية
    priority_breakdown = {}
    for priority in ReportPriority:
        count = (
            db.query(func.count(Report.id))
            .filter(Report.priority == priority)
            .scalar() or 0
        )
        if count > 0:
            priority_breakdown[priority.value] = count

    # 6. التوزيع حسب التصنيف (مع جلب اسم التصنيف)
    from app.models.category import ServiceCategory
    category_breakdown = []
    categories = db.query(ServiceCategory).all()
    for cat in categories:
        count = (
            db.query(func.count(Report.id))
            .filter(Report.category_id == cat.id)
            .scalar() or 0
        )
        if count > 0:
           category_breakdown.append({
            "category_id": cat.id,
            "category_name": cat.name_ar,  #  استخدم name_ar بدلاً من name
            "count": count
            })

    return {
        "total_reports": total_reports,
        "open_reports": open_reports,
        "resolved_reports": resolved_reports,
        "by_status": status_breakdown,
        "by_priority": priority_breakdown,
        "by_category": category_breakdown,
    }


# ---------------------------------------------------------------------------
# Admin report filtering & pagination
# ---------------------------------------------------------------------------

def get_filtered_reports(db: Session, filters: ReportFilterParams) -> dict:
    """
    TASK-01: Apply filters, search, and pagination to the admin report list.
    """
    from sqlalchemy import or_
    
    query = db.query(Report)

    # 1. تطبيق الفلاتر (إذا كانت موجودة)
    if filters.status:
        query = query.filter(Report.status == filters.status)
    if filters.priority:
        query = query.filter(Report.priority == filters.priority)
    if filters.category_id:
        query = query.filter(Report.category_id == filters.category_id)
    if filters.governorate_id:
        query = query.filter(Report.governorate_id == filters.governorate_id)
    if filters.assigned_employee_id:
        query = query.filter(Report.assigned_employee_id == filters.assigned_employee_id)

    # 2. تطبيق البحث (case-insensitive) في reference_number, title, description
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                Report.reference_number.ilike(search_term),
                Report.title.ilike(search_term),
                Report.description.ilike(search_term),
            )
        )

    # 3. حساب العدد الإجمالي قبل تطبيق pagination
    total = query.count()

    # 4. تطبيق pagination
    items = (
        query
        .order_by(Report.created_at.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
        .all()
    )

    # 5. حساب عدد الصفحات الإجمالي
    total_pages = (total + filters.page_size - 1) // filters.page_size

    return {
        "page": filters.page,
        "page_size": filters.page_size,
        "total": total,
        "total_pages": total_pages,
        "items": items,
    }