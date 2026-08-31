"""
app/api/v1/reference_data.py
Public read-only endpoints for governorates, areas, and categories.
No authentication required – any visitor can fetch these lists.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.area import Area
from app.models.category import ServiceCategory
from app.models.governorate import Governorate
from app.schemas.category import CategoryResponse
from app.schemas.location import AreaResponse, GovernorateResponse

router = APIRouter(tags=["Reference Data"])


@router.get("/governorates", response_model=list[GovernorateResponse])
def list_governorates(db: Session = Depends(get_db)):
    """Return all active governorates."""
    return db.query(Governorate).filter(Governorate.is_active == True).all()  # noqa: E712


@router.get("/governorates/{governorate_id}/areas", response_model=list[AreaResponse])
def list_areas(governorate_id: int, db: Session = Depends(get_db)):
    """Return all active areas for a governorate."""
    return (
        db.query(Area)
        .filter(Area.governorate_id == governorate_id, Area.is_active == True)  # noqa: E712
        .all()
    )


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """Return all active service categories."""
    return db.query(ServiceCategory).filter(ServiceCategory.is_active == True).all()  # noqa: E712
