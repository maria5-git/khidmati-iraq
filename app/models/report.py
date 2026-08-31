"""
app/models/report.py
Report model with status and priority enums.
Reference number is generated as IRQ-<year>-<6-digit-sequence>.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from app.database import Base


class ReportStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    rejected = "rejected"
    cancelled = "cancelled"


class ReportPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Human-readable unique reference, e.g. IRQ-2026-000001
    reference_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    citizen_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("service_categories.id", ondelete="RESTRICT"), nullable=False
    )
    governorate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("governorates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    area_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    address_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="reportstatus"),
        nullable=False,
        default=ReportStatus.submitted,
        index=True,
    )
    priority: Mapped[ReportPriority] = mapped_column(
        Enum(ReportPriority, name="reportpriority"),
        nullable=False,
        default=ReportPriority.medium,
        index=True,
    )

    assigned_employee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    citizen: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="reports", foreign_keys=[citizen_id]
    )
    assigned_employee: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="assigned_reports", foreign_keys=[assigned_employee_id]
    )
    category: Mapped["ServiceCategory"] = relationship(  # type: ignore[name-defined]
        "ServiceCategory", back_populates="reports"
    )
    governorate: Mapped["Governorate"] = relationship(  # type: ignore[name-defined]
        "Governorate", back_populates="reports"
    )
    area: Mapped["Area"] = relationship(  # type: ignore[name-defined]
        "Area", back_populates="reports"
    )
    comments: Mapped[list["ReportComment"]] = relationship(  # type: ignore[name-defined]
        "ReportComment", back_populates="report", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ReportStatusHistory"]] = relationship(  # type: ignore[name-defined]
        "ReportStatusHistory", back_populates="report", cascade="all, delete-orphan"
    )


def generate_reference_number(db: Session, year: int) -> str:
    """
    Generate a reference number in the format IRQ-<year>-<6-digit sequence>.

    We count existing reports for the given year and add 1.
    This is safe for low-concurrency educational use.
    For production, use a database sequence instead.
    """
    from sqlalchemy import func, extract

    count = (
        db.query(func.count(Report.id))
        .filter(extract("year", Report.created_at) == year)
        .scalar()
        or 0
    )
    return f"IRQ-{year}-{count + 1:06d}"
