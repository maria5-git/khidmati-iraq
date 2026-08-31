"""
app/models/user.py
User model with role enum.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    citizen = "citizen"
    employee = "employee"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), nullable=False, default=UserRole.citizen
    )
    # Employees are linked to a governorate; citizens are not.
    governorate_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("governorates.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    governorate: Mapped["Governorate"] = relationship(  # type: ignore[name-defined]
        "Governorate", back_populates="users", foreign_keys=[governorate_id]
    )
    reports: Mapped[list["Report"]] = relationship(  # type: ignore[name-defined]
        "Report", back_populates="citizen", foreign_keys="Report.citizen_id"
    )
    assigned_reports: Mapped[list["Report"]] = relationship(  # type: ignore[name-defined]
        "Report", back_populates="assigned_employee", foreign_keys="Report.assigned_employee_id"
    )
    comments: Mapped[list["ReportComment"]] = relationship(  # type: ignore[name-defined]
        "ReportComment", back_populates="author"
    )
