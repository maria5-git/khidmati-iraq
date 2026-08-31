"""
app/models/governorate.py
Iraqi governorate (province) model.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Governorate(Base):
    __tablename__ = "governorates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    areas: Mapped[list["Area"]] = relationship(  # type: ignore[name-defined]
        "Area", back_populates="governorate"
    )
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]
        "User", back_populates="governorate", foreign_keys="User.governorate_id"
    )
    reports: Mapped[list["Report"]] = relationship(  # type: ignore[name-defined]
        "Report", back_populates="governorate"
    )
