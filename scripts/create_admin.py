"""
scripts/create_admin.py
Interactive script to create an admin user account.
Checks whether the email already exists before creating.

Usage:
    python -m scripts.create_admin
"""

import sys

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User, UserRole


def prompt(label: str, secret: bool = False) -> str:
    """Read a non-empty value from stdin."""
    while True:
        if secret:
            import getpass
            value = getpass.getpass(f"{label}: ").strip()
        else:
            value = input(f"{label}: ").strip()
        if value:
            return value
        print("  This field cannot be empty. Please try again.")


def create_admin():
    print("\n=== Create Admin Account ===\n")

    full_name = prompt("Full name")
    email = prompt("Email")
    phone_number = input("Phone number (optional): ").strip() or None
    password = prompt("Password", secret=True)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"\n✗ An account with email '{email}' already exists.")
            sys.exit(1)

        admin = User(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            hashed_password=hash_password(password),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"\n✓ Admin account created successfully!")
        print(f"  Email: {admin.email}")
        print(f"  Role:  {admin.role.value}\n")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
