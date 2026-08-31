"""
tests/conftest.py
Shared test fixtures.

Uses a separate PostgreSQL test database (TEST_DATABASE_URL from .env).
All tables are created fresh before each test module and torn down after.
Each test runs inside a transaction that is rolled back – keeping tests isolated.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.area import Area
from app.models.category import ServiceCategory
from app.models.governorate import Governorate
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Test engine – uses the test database, NOT the development database
# ---------------------------------------------------------------------------

if not settings.test_database_url:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set in .env. "
        "Please create a separate test database and add its URL to .env."
    )

test_engine = create_engine(
    settings.test_database_url,
    echo=False,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# Create / drop all tables once per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables in the test database before any tests run."""
    # Import all models so Base.metadata has every table.
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# Per-test database session (transaction rollback for isolation)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db() -> Session:
    """
    Yield a database session that is rolled back after each test.
    This keeps tests independent without recreating tables each time.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Override the FastAPI get_db dependency to use our test session
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db: Session) -> TestClient:
    """HTTP client that uses the test database session."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed reference data needed by most tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def governorate(db: Session) -> Governorate:
    gov = Governorate(name_ar="بغداد", name_en="Baghdad", is_active=True)
    db.add(gov)
    db.flush()
    return gov


@pytest.fixture()
def governorate2(db: Session) -> Governorate:
    gov = Governorate(name_ar="البصرة", name_en="Basra", is_active=True)
    db.add(gov)
    db.flush()
    return gov


@pytest.fixture()
def area(db: Session, governorate: Governorate) -> Area:
    a = Area(governorate_id=governorate.id, name_ar="الكرخ", name_en="Karkh", is_active=True)
    db.add(a)
    db.flush()
    return a


@pytest.fixture()
def area2(db: Session, governorate2: Governorate) -> Area:
    """Area belonging to a different governorate."""
    a = Area(
        governorate_id=governorate2.id,
        name_ar="أبو الخصيب",
        name_en="Abu Al-Khaseeb",
        is_active=True,
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture()
def category(db: Session) -> ServiceCategory:
    cat = ServiceCategory(
        name_ar="الكهرباء", name_en="Electricity", is_active=True
    )
    db.add(cat)
    db.flush()
    return cat


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

def make_user(
    db: Session,
    email: str,
    role: UserRole,
    governorate_id: int | None = None,
    password: str = "TestPass123!",
) -> User:
    user = User(
        full_name="Test User",
        email=email,
        hashed_password=hash_password(password),
        role=role,
        governorate_id=governorate_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def citizen(db: Session) -> User:
    return make_user(db, "citizen@test.example", UserRole.citizen)


@pytest.fixture()
def citizen2(db: Session) -> User:
    return make_user(db, "citizen2@test.example", UserRole.citizen)


@pytest.fixture()
def employee(db: Session, governorate: Governorate) -> User:
    return make_user(
        db, "employee@test.example", UserRole.employee, governorate_id=governorate.id
    )


@pytest.fixture()
def employee2(db: Session, governorate2: Governorate) -> User:
    """Employee in a different governorate."""
    return make_user(
        db, "employee2@test.example", UserRole.employee, governorate_id=governorate2.id
    )


@pytest.fixture()
def admin(db: Session) -> User:
    return make_user(db, "admin@test.example", UserRole.admin)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def get_token(client: TestClient, email: str, password: str = "TestPass123!") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.json()
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
