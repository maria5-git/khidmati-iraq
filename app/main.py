"""
app/main.py
FastAPI application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.database import check_db_connection

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Khidmati Iraq – A platform for citizens to report public-service problems "
        "in Iraqi cities. Built with FastAPI and PostgreSQL."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS – allow all origins in development
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include all API routes
# ---------------------------------------------------------------------------

app.include_router(api_router)

# ---------------------------------------------------------------------------
# Global exception handler – hide internal details from clients
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Let FastAPI's default HTTPException handler deal with known errors.
    # Only catch truly unexpected exceptions here.
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def health():
    """Simple health check endpoint."""
    db_ok = check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": settings.app_name,
        "database": "connected" if db_ok else "unreachable",
    }


# ---------------------------------------------------------------------------
# Startup event – print a friendly message
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    db_ok = check_db_connection()
    if db_ok:
        print(f"\n[OK] {settings.app_name} started successfully.")
        print(f"  Swagger docs: http://127.0.0.1:8000/docs\n")
    else:
        print(f"\n[!!] {settings.app_name} started but the database is unreachable!")
        print("  Check your DATABASE_URL in .env\n")
