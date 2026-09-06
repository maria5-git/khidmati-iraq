"""
tests/test_admin.py
Tests for admin endpoints (TASK-01, TASK-04, TASK-08)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import auth_header, get_token


def test_admin_can_assign_report(
    client: TestClient,
    db: Session,
    admin: User,
    employee: User,
    citizen: User,
    category,
    governorate,
    area,
):
    """TASK-04: Admin can assign a report to an employee."""
    # 1. Citizen creates report
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    response = client.post(
        "/api/v1/reports",
        json={
            "category_id": category.id,
            "governorate_id": governorate.id,
            "area_id": area.id,
            "title": "Assignment Test",
            "description": "Testing assignment",
        },
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
    data = response.json()
    assert data["status"] == "assigned"
    assert data["assigned_employee_id"] == employee.id


def test_admin_cannot_assign_cross_governorate(
    client: TestClient,
    db: Session,
    admin: User,
    employee2: User,  # Employee in different governorate
    citizen: User,
    category,
    governorate,
    area,
):
    """TASK-04: Reject assignment if employee doesn't belong to report's governorate."""
    # 1. Citizen creates report in governorate 1
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    response = client.post(
        "/api/v1/reports",
        json={
            "category_id": category.id,
            "governorate_id": governorate.id,
            "area_id": area.id,
            "title": "Cross Governorate Test",
            "description": "Testing cross-governorate rejection",
        },
        headers=citizen_headers,
    )
    assert response.status_code == 201
    report_id = response.json()["id"]

    # 2. Admin tries to assign to employee from different governorate
    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    response = client.patch(
        f"/api/v1/admin/reports/{report_id}/assign",
        json={"employee_id": employee2.id},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "Employee does not belong to the same governorate" in response.text


def test_admin_can_filter_reports(
    client: TestClient,
    db: Session,
    admin: User,
    citizen: User,
    category,
    governorate,
    area,
):
    """TASK-01: Admin can filter reports by status and search."""
    # 1. Create multiple reports
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    
    # Report 1: submitted
    client.post(
        "/api/v1/reports",
        json={
            "category_id": category.id,
            "governorate_id": governorate.id,
            "area_id": area.id,
            "title": "First Report",
            "description": "This is the first report",
        },
        headers=citizen_headers,
    )
    
    # Report 2: submitted with different title
    client.post(
        "/api/v1/reports",
        json={
            "category_id": category.id,
            "governorate_id": governorate.id,
            "area_id": area.id,
            "title": "Second Report",
            "description": "This is the second report",
        },
        headers=citizen_headers,
    )

    # 2. Admin filters by status
    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    response = client.get(
        "/api/v1/admin/reports?status=submitted&page=1&page_size=10",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert all(r["status"] == "submitted" for r in data["items"])

    # 3. Admin searches by keyword
    response = client.get(
        "/api/v1/admin/reports?search=First&page=1&page_size=10",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("First" in r["title"] for r in data["items"])


def test_admin_dashboard(
    client: TestClient,
    db: Session,
    admin: User,
    citizen: User,
    category,
    governorate,
    area,
):
    """TASK-08: Admin dashboard returns correct statistics."""
    # 1. Create reports
    citizen_token = get_token(client, citizen.email)
    citizen_headers = auth_header(citizen_token)
    
    for i in range(3):
        client.post(
            "/api/v1/reports",
            json={
                "category_id": category.id,
                "governorate_id": governorate.id,
                "area_id": area.id,
                "title": f"Dashboard Report {i}",
                "description": f"Test report {i}",
            },
            headers=citizen_headers,
        )

    # 2. Admin dashboard
    admin_token = get_token(client, admin.email)
    admin_headers = auth_header(admin_token)
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "total_reports" in data
    assert "open_reports" in data
    assert "resolved_reports" in data
    assert "by_status" in data
    assert "by_priority" in data
    assert "by_category" in data
    
    # Check that counts make sense
    assert data["total_reports"] >= 3
    assert data["open_reports"] >= 3
    assert data["resolved_reports"] == 0  # None resolved yet


def test_non_admin_cannot_access_dashboard(
    client: TestClient,
    db: Session,
    citizen: User,
):
    """TASK-08: Non-admin users cannot access dashboard."""
    token = get_token(client, citizen.email)
    headers = auth_header(token)
    
    response = client.get("/api/v1/admin/dashboard", headers=headers)
    assert response.status_code == 403