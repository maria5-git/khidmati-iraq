"""
tests/test_reports.py
Tests for citizen report endpoints (TASK-02, 03, 05, 06, 07)
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
# TASK-02, TASK-03: Create & Validate
# ---------------------------------------------------------------------------

def test_citizen_creates_report(
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


def test_citizen_cannot_create_report_with_wrong_area(
    client: TestClient,
    citizen: User,
    category: ServiceCategory,
    governorate: Governorate,
    area2: Area,  # belongs to different governorate
):
    token = get_token(client, citizen.email)
    headers = auth_header(token)
    response = client.post(
        "/api/v1/reports",
        json={
            "category_id": category.id,
            "governorate_id": governorate.id,  # Baghdad
            "area_id": area2.id,               # belongs to Basra
            "title": "Invalid Report",
            "description": "This should fail",
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "Area does not belong" in response.text


# ---------------------------------------------------------------------------
# TASK-02: Ownership
# ---------------------------------------------------------------------------

def test_citizen_can_view_own_report(
    client: TestClient,
    citizen: User,
    category: ServiceCategory,
    governorate: Governorate,
    area: Area,
):
    token = get_token(client, citizen.email)
    headers = auth_header(token)
    response = client.post(
        "/api/v1/reports",
        json=create_report_payload(category.id, governorate.id, area.id),
        headers=headers,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    response = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == report_id


def test_citizen_cannot_view_other_report(
    client: TestClient,
    citizen: User,
    citizen2: User,
    category: ServiceCategory,
    governorate: Governorate,
    area: Area,
):
    # Citizen1 creates a report
    token1 = get_token(client, citizen.email)
    headers1 = auth_header(token1)
    response = client.post(
        "/api/v1/reports",
        json=create_report_payload(category.id, governorate.id, area.id),
        headers=headers1,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    # Citizen2 tries to view it
    token2 = get_token(client, citizen2.email)
    headers2 = auth_header(token2)
    response = client.get(f"/api/v1/reports/{report_id}", headers=headers2)
    assert response.status_code == 404
    assert "Report not found" in response.text


# ---------------------------------------------------------------------------
# TASK-05: Status workflow
# ---------------------------------------------------------------------------

def test_employee_can_update_status(
    client: TestClient,
    db: Session,
    citizen: User,
    employee: User,
    admin: User,
    category: ServiceCategory,
    governorate: Governorate,
    area: Area,
):
    # 1. Citizen creates report
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    response = client.post(
        "/api/v1/reports",
        json=create_report_payload(category.id, governorate.id, area.id),
        headers=citizen_headers,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    # 2. Admin assigns report
    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    response = client.patch(
        f"/api/v1/admin/reports/{report_id}/assign",
        json={"employee_id": employee.id, "note": "Assigned for testing"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "assigned"

    # 3. Employee changes status to "in_progress"
    employee_token = get_token(client, employee.email)
    employee_headers = auth_header(employee_token)
    response = client.patch(
        f"/api/v1/employee/reports/{report_id}/status",
        json={"new_status": "in_progress"},
        headers=employee_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_invalid_status_transition_rejected(
    client: TestClient,
    db: Session,
    citizen: User,
    employee: User,
    admin: User,
    category: ServiceCategory,
    governorate: Governorate,
    area: Area,
):
    # 1. Create report
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    response = client.post(
        "/api/v1/reports",
        json=create_report_payload(category.id, governorate.id, area.id),
        headers=citizen_headers,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    # 2. Admin assigns
    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    client.patch(
        f"/api/v1/admin/reports/{report_id}/assign",
        json={"employee_id": employee.id},
        headers=admin_headers,
    )

    # 3. Employee tries invalid transition: assigned -> resolved (skip in_progress)
    employee_token = get_token(client, employee.email)
    employee_headers = auth_header(employee_token)
    response = client.patch(
        f"/api/v1/employee/reports/{report_id}/status",
        json={"new_status": "resolved"},
        headers=employee_headers,
    )
    # Should be 422 (Unprocessable) because transition is not allowed
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert "Cannot transition from 'assigned' to 'resolved'" in data["detail"]["error"]["message"]


# ---------------------------------------------------------------------------
# TASK-06: Internal notes
# ---------------------------------------------------------------------------

def test_employee_can_add_internal_note(
    client: TestClient,
    db: Session,
    citizen: User,
    employee: User,
    admin: User,
    category: ServiceCategory,
    governorate: Governorate,
    area: Area,
):
    # 1. Create report
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    response = client.post(
        "/api/v1/reports",
        json=create_report_payload(category.id, governorate.id, area.id),
        headers=citizen_headers,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    # 2. Admin assigns
    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    client.patch(
        f"/api/v1/admin/reports/{report_id}/assign",
        json={"employee_id": employee.id},
        headers=admin_headers,
    )

    # 3. Employee adds internal note
    employee_token = get_token(client, employee.email)
    employee_headers = auth_header(employee_token)
    response = client.post(
        f"/api/v1/employee/reports/{report_id}/internal-notes",
        json={"content": "This is an internal note"},
        headers=employee_headers,
    )
    assert response.status_code == 201
    assert response.json()["content"] == "This is an internal note"
    assert response.json()["is_internal"] is True

    # 4. Citizen tries to view comments (should NOT see internal note)
    response = client.get(f"/api/v1/reports/{report_id}/comments", headers=citizen_headers)
    assert response.status_code == 200
    comments = response.json()
    assert all(not c["is_internal"] for c in comments)


# ---------------------------------------------------------------------------
# TASK-07: Resolution
# ---------------------------------------------------------------------------

def test_resolve_report_without_summary_fails(
    client: TestClient,
    db: Session,
    citizen: User,
    employee: User,
    category,
    governorate,
    area,
    admin: User,
):
    """TASK-07: Resolve with empty summary fails (either 400 or 422)."""
    # 1. Create report
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    response = client.post(
        "/api/v1/reports",
        json={
            "category_id": category.id,
            "governorate_id": governorate.id,
            "area_id": area.id,
            "title": "Resolution Test",
            "description": "Testing resolution",
        },
        headers=citizen_headers,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    # 2. Admin assigns
    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    client.patch(
        f"/api/v1/admin/reports/{report_id}/assign",
        json={"employee_id": employee.id},
        headers=admin_headers,
    )

    # 3. Employee changes to "in_progress"
    employee_token = get_token(client, employee.email)
    employee_headers = auth_header(employee_token)
    client.patch(
        f"/api/v1/employee/reports/{report_id}/status",
        json={"new_status": "in_progress"},
        headers=employee_headers,
    )

    # 4. Resolve with empty summary (should fail)
    response = client.post(
        f"/api/v1/employee/reports/{report_id}/resolve",
        json={"resolution_summary": ""},
        headers=employee_headers,
    )
    # قد يعيد 400 (من الخدمة) أو 422 (من الـ Schema)
    assert response.status_code in (400, 422)
    
    # تحقق من وجود رسالة خطأ متعلقة بالملخص
    data = response.json()
    if "detail" in data:
        if isinstance(data["detail"], list):
            # إذا كان الخطأ من Pydantic (422)
            assert any(
                "resolution_summary" in str(err.get("loc", []))
                for err in data["detail"]
                if isinstance(err, dict)
            )
        else:
            # إذا كان الخطأ من الخدمة (400)
            assert "resolution" in str(data["detail"]).lower() or "summary" in str(data["detail"]).lower()


def test_resolve_report_with_summary_succeeds(
    client: TestClient,
    db: Session,
    citizen: User,
    employee: User,
    admin: User,
    category: ServiceCategory,
    governorate: Governorate,
    area: Area,
):
    # 1. Create & assign & set in_progress
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    response = client.post(
        "/api/v1/reports",
        json=create_report_payload(category.id, governorate.id, area.id),
        headers=citizen_headers,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    client.patch(
        f"/api/v1/admin/reports/{report_id}/assign",
        json={"employee_id": employee.id},
        headers=admin_headers,
    )

    employee_token = get_token(client, employee.email)
    employee_headers = auth_header(employee_token)
    client.patch(
        f"/api/v1/employee/reports/{report_id}/status",
        json={"new_status": "in_progress"},
        headers=employee_headers,
    )

    # 2. Resolve with summary (should succeed)
    response = client.post(
        f"/api/v1/employee/reports/{report_id}/resolve",
        json={"resolution_summary": "Fixed the issue successfully"},
        headers=employee_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["resolution_summary"] == "Fixed the issue successfully"
    assert data["resolved_at"] is not None