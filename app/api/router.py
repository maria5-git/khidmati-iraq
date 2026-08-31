"""
app/api/router.py
Central router that assembles all v1 sub-routers.
"""

from fastapi import APIRouter

from app.api.v1 import auth, reference_data, reports, employee, admin
from app.config import settings

api_router = APIRouter(prefix=settings.api_v1_prefix)

api_router.include_router(auth.router)
api_router.include_router(reference_data.router)
api_router.include_router(reports.router)
api_router.include_router(employee.router)
api_router.include_router(admin.router)
