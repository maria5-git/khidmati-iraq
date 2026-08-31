# app/models/__init__.py
# Import all models here so Alembic can detect them automatically.

from app.models.user import User, UserRole          # noqa: F401
from app.models.governorate import Governorate      # noqa: F401
from app.models.area import Area                    # noqa: F401
from app.models.category import ServiceCategory     # noqa: F401
from app.models.report import Report, ReportStatus, ReportPriority  # noqa: F401
from app.models.comment import ReportComment        # noqa: F401
from app.models.status_history import ReportStatusHistory  # noqa: F401
