"""
scripts/seed.py
Populate the database with initial reference data, test accounts, and
sample reports.  Safe to run multiple times (uses get-or-create logic).

Usage:
    python -m scripts.seed
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.area import Area
from app.models.category import ServiceCategory
from app.models.comment import ReportComment
from app.models.governorate import Governorate
from app.models.report import Report, ReportPriority, ReportStatus, generate_reference_number
from app.models.status_history import ReportStatusHistory
from app.models.user import User, UserRole
from app.config import settings


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

GOVERNORATES = [
    {"name_ar": "بغداد",  "name_en": "Baghdad"},
    {"name_ar": "البصرة", "name_en": "Basra"},
    {"name_ar": "نينوى",  "name_en": "Nineveh"},
    {"name_ar": "أربيل",  "name_en": "Erbil"},
    {"name_ar": "النجف",  "name_en": "Najaf"},
    {"name_ar": "كربلاء", "name_en": "Karbala"},
    {"name_ar": "الأنبار","name_en": "Anbar"},
    {"name_ar": "ذي قار","name_en": "Dhi Qar"},
]

AREAS = {
    "Baghdad":  [
        {"name_ar": "الكرخ",       "name_en": "Karkh"},
        {"name_ar": "الرصافة",     "name_en": "Rusafa"},
        {"name_ar": "الكاظمية",    "name_en": "Kadhimiya"},
        {"name_ar": "المنصور",     "name_en": "Mansour"},
    ],
    "Basra":    [
        {"name_ar": "أبو الخصيب", "name_en": "Abu Al-Khaseeb"},
        {"name_ar": "المعقل",     "name_en": "Al-Maqal"},
        {"name_ar": "الزبير",     "name_en": "Al-Zubair"},
    ],
    "Nineveh":  [
        {"name_ar": "الموصل الأيسر", "name_en": "Left Bank Mosul"},
        {"name_ar": "الموصل الأيمن", "name_en": "Right Bank Mosul"},
    ],
    "Erbil":    [
        {"name_ar": "أربيل المركز", "name_en": "Erbil Center"},
        {"name_ar": "شقلاوة",       "name_en": "Shaqlawa"},
    ],
    "Najaf":    [
        {"name_ar": "النجف المركز", "name_en": "Najaf Center"},
        {"name_ar": "الكوفة",       "name_en": "Kufa"},
    ],
    "Karbala":  [
        {"name_ar": "كربلاء المركز", "name_en": "Karbala Center"},
        {"name_ar": "الهندية",       "name_en": "Hindiya"},
    ],
    "Anbar":    [
        {"name_ar": "الرمادي", "name_en": "Ramadi"},
        {"name_ar": "الفلوجة", "name_en": "Fallujah"},
    ],
    "Dhi Qar": [
        {"name_ar": "الناصرية", "name_en": "Nasiriyah"},
        {"name_ar": "الشطرة",   "name_en": "Shatrah"},
    ],
}

CATEGORIES = [
    {"name_ar": "الكهرباء",        "name_en": "Electricity",     "description": "Power outages and electrical infrastructure issues"},
    {"name_ar": "الماء",           "name_en": "Water",           "description": "Water supply and quality problems"},
    {"name_ar": "الطرق",           "name_en": "Roads",           "description": "Damaged roads, potholes, and street repairs"},
    {"name_ar": "النفايات",        "name_en": "Waste",           "description": "Garbage accumulation and waste management"},
    {"name_ar": "إضاءة الشوارع",   "name_en": "Street Lighting", "description": "Broken or missing street lights"},
    {"name_ar": "الصرف الصحي",     "name_en": "Sewage",          "description": "Sewage leaks and drainage problems"},
    {"name_ar": "أخرى",            "name_en": "Other",           "description": "Other public-service issues"},
]

ACCOUNTS = [
    {
        "full_name": "Admin User",
        "email": "admin@khidmati.local",
        "phone_number": "+9647001000001",
        "role": UserRole.admin,
        "governorate": None,
    },
    {
        "full_name": "Baghdad Employee",
        "email": "employee.baghdad@khidmati.local",
        "phone_number": "+9647001000002",
        "role": UserRole.employee,
        "governorate": "Baghdad",
    },
    {
        "full_name": "Basra Employee",
        "email": "employee.basra@khidmati.local",
        "phone_number": "+9647001000003",
        "role": UserRole.employee,
        "governorate": "Basra",
    },
    {
        "full_name": "Ahmed Al-Rashid",
        "email": "citizen1@khidmati.local",
        "phone_number": "+9647001000004",
        "role": UserRole.citizen,
        "governorate": None,
    },
    {
        "full_name": "Fatima Hassan",
        "email": "citizen2@khidmati.local",
        "phone_number": "+9647001000005",
        "role": UserRole.citizen,
        "governorate": None,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create_governorate(db: Session, data: dict) -> Governorate:
    gov = db.query(Governorate).filter(Governorate.name_en == data["name_en"]).first()
    if not gov:
        gov = Governorate(**data)
        db.add(gov)
        db.flush()
    return gov


def get_or_create_area(db: Session, governorate: Governorate, data: dict) -> Area:
    area = (
        db.query(Area)
        .filter(Area.governorate_id == governorate.id, Area.name_en == data["name_en"])
        .first()
    )
    if not area:
        area = Area(governorate_id=governorate.id, **data)
        db.add(area)
        db.flush()
    return area


def get_or_create_category(db: Session, data: dict) -> ServiceCategory:
    cat = db.query(ServiceCategory).filter(ServiceCategory.name_en == data["name_en"]).first()
    if not cat:
        cat = ServiceCategory(**data)
        db.add(cat)
        db.flush()
    return cat


def get_or_create_user(db: Session, data: dict, gov_map: dict) -> User:
    user = db.query(User).filter(User.email == data["email"]).first()
    if not user:
        gov_id = None
        if data["governorate"]:
            gov_id = gov_map[data["governorate"]].id
        user = User(
            full_name=data["full_name"],
            email=data["email"],
            phone_number=data["phone_number"],
            hashed_password=hash_password(settings.seed_default_password),
            role=data["role"],
            governorate_id=gov_id,
            is_active=True,
        )
        db.add(user)
        db.flush()
    return user


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed():
    db = SessionLocal()
    try:
        print("Seeding governorates...")
        gov_map: dict[str, Governorate] = {}
        for g in GOVERNORATES:
            gov = get_or_create_governorate(db, g)
            gov_map[g["name_en"]] = gov

        print("Seeding areas...")
        area_map: dict[str, dict[str, Area]] = {}
        for gov_en, areas in AREAS.items():
            area_map[gov_en] = {}
            gov = gov_map[gov_en]
            for a in areas:
                area = get_or_create_area(db, gov, a)
                area_map[gov_en][a["name_en"]] = area

        print("Seeding categories...")
        cat_map: dict[str, ServiceCategory] = {}
        for c in CATEGORIES:
            cat = get_or_create_category(db, c)
            cat_map[c["name_en"]] = cat

        print("Seeding accounts...")
        user_map: dict[str, User] = {}
        for acc in ACCOUNTS:
            user = get_or_create_user(db, acc, gov_map)
            user_map[acc["email"]] = user

        db.commit()

        # ----------------------------------------------------------------
        # Sample reports
        # ----------------------------------------------------------------
        print("Seeding sample reports...")

        citizen1 = user_map["citizen1@khidmati.local"]
        citizen2 = user_map["citizen2@khidmati.local"]
        emp_baghdad = user_map["employee.baghdad@khidmati.local"]
        emp_basra = user_map["employee.basra@khidmati.local"]
        admin = user_map["admin@khidmati.local"]

        baghdad = gov_map["Baghdad"]
        basra = gov_map["Basra"]
        karkh = area_map["Baghdad"]["Karkh"]
        rusafa = area_map["Baghdad"]["Rusafa"]
        abu_al_khaseeb = area_map["Basra"]["Abu Al-Khaseeb"]

        sample_reports = [
            {
                "citizen": citizen1,
                "category": cat_map["Electricity"],
                "governorate": baghdad,
                "area": karkh,
                "title": "Power outage lasting 12 hours in Karkh",
                "description": "The entire neighbourhood has been without electricity for over 12 hours. Residents are struggling in the heat.",
                "address_details": "Near Al-Karkh hospital, Block 5",
                "status": ReportStatus.in_progress,
                "priority": ReportPriority.urgent,
                "employee": emp_baghdad,
            },
            {
                "citizen": citizen1,
                "category": cat_map["Roads"],
                "governorate": baghdad,
                "area": rusafa,
                "title": "Large pothole on main road in Rusafa",
                "description": "A dangerous pothole has appeared on the main road causing accidents and traffic jams.",
                "address_details": "Al-Rashid Street, opposite the post office",
                "status": ReportStatus.under_review,
                "priority": ReportPriority.high,
                "employee": None,
            },
            {
                "citizen": citizen2,
                "category": cat_map["Water"],
                "governorate": basra,
                "area": abu_al_khaseeb,
                "title": "No water supply for three days",
                "description": "Residents of Abu Al-Khaseeb have had no water supply for three consecutive days.",
                "address_details": "District 7, near the school",
                "status": ReportStatus.resolved,
                "priority": ReportPriority.urgent,
                "employee": emp_basra,
                "resolution": "The main water pump was repaired and water supply restored on schedule.",
            },
            {
                "citizen": citizen2,
                "category": cat_map["Waste"],
                "governorate": baghdad,
                "area": karkh,
                "title": "Uncollected garbage piling up for a week",
                "description": "Garbage has not been collected for over a week, causing a health hazard and bad smell.",
                "address_details": "Block 3, Al-Karkh",
                "status": ReportStatus.submitted,
                "priority": ReportPriority.medium,
                "employee": None,
            },
            {
                "citizen": citizen1,
                "category": cat_map["Street Lighting"],
                "governorate": baghdad,
                "area": rusafa,
                "title": "Street lights not working on Al-Jumhuriya Bridge",
                "description": "Several street lights on Al-Jumhuriya Bridge have been broken for two weeks, creating a safety hazard at night.",
                "address_details": "Al-Jumhuriya Bridge, Rusafa side",
                "status": ReportStatus.assigned,
                "priority": ReportPriority.medium,
                "employee": emp_baghdad,
            },
        ]

        created_reports = []
        for r in sample_reports:
            # Check if this report already exists by title to allow re-seeding.
            existing = db.query(Report).filter(Report.title == r["title"]).first()
            if existing:
                created_reports.append(existing)
                continue

            year = datetime.now(timezone.utc).year
            ref = generate_reference_number(db, year)

            report = Report(
                reference_number=ref,
                citizen_id=r["citizen"].id,
                category_id=r["category"].id,
                governorate_id=r["governorate"].id,
                area_id=r["area"].id,
                title=r["title"],
                description=r["description"],
                address_details=r.get("address_details"),
                status=r["status"],
                priority=r["priority"],
                assigned_employee_id=r["employee"].id if r.get("employee") else None,
                resolution_summary=r.get("resolution"),
                resolved_at=datetime.now(timezone.utc) if r["status"] == ReportStatus.resolved else None,
            )
            db.add(report)
            db.flush()

            # Initial status history
            history = ReportStatusHistory(
                report_id=report.id,
                previous_status=None,
                new_status=ReportStatus.submitted.value,
                changed_by_id=r["citizen"].id,
                note="Report submitted by citizen.",
            )
            db.add(history)

            # Add more history entries to match the current status
            if r["status"] == ReportStatus.under_review:
                db.add(ReportStatusHistory(
                    report_id=report.id,
                    previous_status=ReportStatus.submitted.value,
                    new_status=ReportStatus.under_review.value,
                    changed_by_id=emp_baghdad.id,
                    note="Report taken under review.",
                ))
            elif r["status"] in (ReportStatus.assigned, ReportStatus.in_progress):
                db.add(ReportStatusHistory(
                    report_id=report.id,
                    previous_status=ReportStatus.submitted.value,
                    new_status=ReportStatus.under_review.value,
                    changed_by_id=admin.id,
                    note="Report taken under review.",
                ))
                db.add(ReportStatusHistory(
                    report_id=report.id,
                    previous_status=ReportStatus.under_review.value,
                    new_status=ReportStatus.assigned.value,
                    changed_by_id=admin.id,
                    note=f"Assigned to {r['employee'].full_name}.",
                ))
                if r["status"] == ReportStatus.in_progress:
                    db.add(ReportStatusHistory(
                        report_id=report.id,
                        previous_status=ReportStatus.assigned.value,
                        new_status=ReportStatus.in_progress.value,
                        changed_by_id=r["employee"].id,
                        note="Work started.",
                    ))
            elif r["status"] == ReportStatus.resolved:
                emp = r["employee"]
                db.add(ReportStatusHistory(
                    report_id=report.id,
                    previous_status=ReportStatus.submitted.value,
                    new_status=ReportStatus.under_review.value,
                    changed_by_id=emp.id,
                    note="Report reviewed.",
                ))
                db.add(ReportStatusHistory(
                    report_id=report.id,
                    previous_status=ReportStatus.under_review.value,
                    new_status=ReportStatus.assigned.value,
                    changed_by_id=admin.id,
                    note=f"Assigned to {emp.full_name}.",
                ))
                db.add(ReportStatusHistory(
                    report_id=report.id,
                    previous_status=ReportStatus.assigned.value,
                    new_status=ReportStatus.in_progress.value,
                    changed_by_id=emp.id,
                    note="Work started.",
                ))
                db.add(ReportStatusHistory(
                    report_id=report.id,
                    previous_status=ReportStatus.in_progress.value,
                    new_status=ReportStatus.resolved.value,
                    changed_by_id=emp.id,
                    note="Issue resolved.",
                ))

            # Sample comments
            db.add(ReportComment(
                report_id=report.id,
                author_id=r["citizen"].id,
                content="Please fix this as soon as possible, it is affecting daily life.",
                is_internal=False,
            ))
            if r.get("employee"):
                db.add(ReportComment(
                    report_id=report.id,
                    author_id=r["employee"].id,
                    content="We have received your report and are working on it.",
                    is_internal=False,
                ))
                db.add(ReportComment(
                    report_id=report.id,
                    author_id=r["employee"].id,
                    content="Need to check spare parts availability before confirming schedule.",
                    is_internal=True,
                ))

            created_reports.append(report)

        db.commit()
        print(f"  Created/verified {len(created_reports)} sample reports.")

        # ----------------------------------------------------------------
        # Print credentials
        # ----------------------------------------------------------------
        print("\n" + "=" * 60)
        print("  SEED COMPLETE – Login Credentials")
        print("=" * 60)
        print(f"  Password for all accounts: {settings.seed_default_password}")
        print()
        for acc in ACCOUNTS:
            role_label = acc["role"].value.upper()
            print(f"  [{role_label:8}] {acc['email']}")
        print("=" * 60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
