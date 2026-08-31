"""
tests/test_auth.py
Authentication tests:
  - citizen registration
  - successful login
  - incorrect password rejected
  - inactive user rejected
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import auth_header, get_token


class TestRegister:
    def test_citizen_registers_successfully(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "New Citizen",
                "email": "newcitizen@test.example",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newcitizen@test.example"
        assert data["role"] == "citizen"
        # Password must never be returned.
        assert "password" not in data
        assert "hashed_password" not in data

    def test_duplicate_email_rejected(self, client: TestClient, citizen: User):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Duplicate",
                "email": citizen.email,
                "password": "AnotherPass123!",
            },
        )
        assert response.status_code == 409

    def test_invalid_email_rejected(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Bad Email",
                "email": "not-an-email",
                "password": "Pass123!",
            },
        )
        assert response.status_code == 422  # Pydantic validation error


class TestLogin:
    def test_successful_login_returns_token(self, client: TestClient, citizen: User):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": citizen.email, "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == citizen.email

    def test_wrong_password_rejected(self, client: TestClient, citizen: User):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": citizen.email, "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    def test_unknown_email_rejected(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.local", "password": "SomePass123!"},
        )
        assert response.status_code == 401

    def test_inactive_user_rejected(
        self, client: TestClient, db: Session, citizen: User
    ):
        # Deactivate the citizen.
        citizen.is_active = False
        db.flush()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": citizen.email, "password": "TestPass123!"},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["error"]["code"] == "INACTIVE_USER"


class TestMe:
    def test_me_returns_current_user(self, client: TestClient, citizen: User):
        token = get_token(client, citizen.email)
        response = client.get("/api/v1/auth/me", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["email"] == citizen.email

    def test_me_requires_authentication(self, client: TestClient):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
