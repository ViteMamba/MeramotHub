"""
Comprehensive seed script for MeramotHub.
Seeds: admin user, area_manager user, service categories, and service items.
Safe to run multiple times (idempotent).
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.service import ServiceCategory, ServiceItem
from app.models.service_provider import SkillCategory
from app.utils.auth import hash_password


def seed_users(db: Session):
    """Seed admin and area_manager users."""
    users_data = [
        {
            "full_name": "MeramotHub Admin",
            "phone_number": "01700000001",
            "email": "admin@meramothub.com",
            "password": "admin123",
            "role": UserRole.admin,
        },
        {
            "full_name": "Dhaka Area Manager",
            "phone_number": "01700000002",
            "email": "manager@meramothub.com",
            "password": "manager123",
            "role": UserRole.area_manager,
        },
    ]

    for user_data in users_data:
        existing = db.query(User).filter(User.phone_number == user_data["phone_number"]).first()
        if existing:
            print(f"  User '{user_data['full_name']}' already exists, skipping.")
            continue

        new_user = User(
            full_name=user_data["full_name"],
            phone_number=user_data["phone_number"],
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            role=user_data["role"],
            is_active=True,
            is_verified=True,
        )
        db.add(new_user)
        print(f"  Created user: {user_data['full_name']} ({user_data['role'].value})")


def seed_services(db: Session):
    """Seed service categories and items."""
    categories_data = [
        {"name": "AC Services", "description": "Installation, repair and maintenance of ACs", "skill_required": SkillCategory.ac_mechanic},
        {"name": "Plumbing Services", "description": "Fixing leaks, pipes and bathroom fittings", "skill_required": SkillCategory.plumber},
        {"name": "Electrical Services", "description": "Fan, light and wiring solutions", "skill_required": SkillCategory.electrician},
        {"name": "Carpentry Services", "description": "Furniture repair, door/window fixing", "skill_required": SkillCategory.carpenter},
        {"name": "Painting Services", "description": "Wall painting, waterproofing, polishing", "skill_required": SkillCategory.painter},
    ]

    category_map = {}
    for cat_data in categories_data:
        existing = db.query(ServiceCategory).filter(ServiceCategory.name == cat_data["name"]).first()
        if existing:
            category_map[cat_data["name"]] = existing
            print(f"  Category '{cat_data['name']}' already exists, skipping.")
        else:
            new_cat = ServiceCategory(**cat_data)
            db.add(new_cat)
            db.flush()
            category_map[cat_data["name"]] = new_cat
            print(f"  Created category: {cat_data['name']}")

    items_data = [
        {"category": "AC Services", "name": "AC Master Service", "base_price": 1500, "unit": "per unit"},
        {"category": "AC Services", "name": "AC Gas Refill", "base_price": 2500, "unit": "per unit"},
        {"category": "AC Services", "name": "AC Installation", "base_price": 3000, "unit": "per unit"},
        {"category": "Plumbing Services", "name": "Tap Leak Repair", "base_price": 300, "unit": "per job"},
        {"category": "Plumbing Services", "name": "Commode Installation", "base_price": 1200, "unit": "per unit"},
        {"category": "Plumbing Services", "name": "Pipe Fitting", "base_price": 500, "unit": "per job"},
        {"category": "Electrical Services", "name": "Fan Installation", "base_price": 400, "unit": "per unit"},
        {"category": "Electrical Services", "name": "Whole House Wiring Check", "base_price": 1000, "unit": "per visit"},
        {"category": "Electrical Services", "name": "Switch/Socket Replacement", "base_price": 200, "unit": "per unit"},
        {"category": "Carpentry Services", "name": "Door Lock Repair", "base_price": 350, "unit": "per unit"},
        {"category": "Carpentry Services", "name": "Furniture Assembly", "base_price": 800, "unit": "per job"},
        {"category": "Painting Services", "name": "Room Painting (per wall)", "base_price": 1500, "unit": "per wall"},
        {"category": "Painting Services", "name": "Waterproofing", "base_price": 2000, "unit": "per sq ft"},
    ]

    for item_data in items_data:
        cat = category_map.get(item_data["category"])
        if not cat:
            print(f"  Warning: Category '{item_data['category']}' not found, skipping item '{item_data['name']}'")
            continue
        existing = db.query(ServiceItem).filter(
            ServiceItem.category_id == cat.id,
            ServiceItem.name == item_data["name"]
        ).first()
        if existing:
            print(f"  Item '{item_data['name']}' already exists, skipping.")
        else:
            new_item = ServiceItem(
                category_id=cat.id,
                name=item_data["name"],
                base_price=item_data["base_price"],
                unit=item_data["unit"],
            )
            db.add(new_item)
            print(f"  Created item: {item_data['name']}")


def run_seed():
    db: Session = SessionLocal()
    try:
        print("\n--- Seeding Users ---")
        seed_users(db)

        print("\n--- Seeding Services ---")
        seed_services(db)

        db.commit()
        print("\n✅ Seed complete!")
    except Exception as e:
        print(f"\n❌ Error seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
