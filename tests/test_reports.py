"""
tests/test_reports.py
Report management tests.
TODO (TASK-09): Add tests for all project requirements.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.category import ServiceCategory
from app.models.governorate import Governorate
from app.models.user import User
from tests.conftest import auth_header, get_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_report_payload(
    category_id: int,
    governorate_id: int,
    area_id: int,
    title: str = "Test report title here",
    description: str = "Test report description with enough detail.",
) -> dict:
    return {
        "category_id": category_id,
        "governorate_id": governorate_id,
        "area_id": area_id,
        "title": title,
        "description": description,
        "address_details": "Some street, block 1",
    }


def post_report(
    client: TestClient,
    token: str,
    category: ServiceCategory,
    governorate: Governorate,
    area: Area,
) -> dict:
    resp = client.post(
        "/api/v1/reports",
        json=create_report_payload(category.id, governorate.id, area.id),
        headers=auth_header(token),
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


# ---------------------------------------------------------------------------
# Citizen creates a report
# ---------------------------------------------------------------------------

class TestCreateReport:
    def test_citizen_creates_report(
        self,
        client: TestClient,
        citizen: User,
        category: ServiceCategory,
        governorate: Governorate,
        area: Area,
    ):
        token = get_token(client, citizen.email)
        report = post_report(client, token, category, governorate, area)

        assert report["status"] == "submitted"
        assert report["citizen_id"] == citizen.id
        assert report["reference_number"].startswith("IRQ-")


# ---------------------------------------------------------------------------
# Citizen views reports
# ---------------------------------------------------------------------------

class TestViewReport:
    def test_citizen_views_report(
        self,
        client: TestClient,
        citizen: User,
        category: ServiceCategory,
        governorate: Governorate,
        area: Area,
    ):
        token = get_token(client, citizen.email)
        created = post_report(client, token, category, governorate, area)
        report_id = created["id"]

        resp = client.get(f"/api/v1/reports/{report_id}", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == report_id
