from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.service import ServiceCategory, ServiceItem
from app.models.service_provider import SkillCategory

def seed_services():
    db: Session = SessionLocal()
    try:
        # Categories
        cat_ac = ServiceCategory(name="AC Services", description="Installation, repair and maintenance of ACs", skill_required=SkillCategory.ac_mechanic)
        cat_plumb = ServiceCategory(name="Plumbing Services", description="Fixing leaks, pipes and bathroom fittings", skill_required=SkillCategory.plumber)
        cat_elec = ServiceCategory(name="Electrical Services", description="Fan, light and wiring solutions", skill_required=SkillCategory.electrician)
        
        db.add_all([cat_ac, cat_plumb, cat_elec])
        db.commit()
        
        # Items
        items = [
            ServiceItem(category_id=cat_ac.id, name="AC Master Service", base_price=1500, unit="per unit"),
            ServiceItem(category_id=cat_ac.id, name="AC Gas Refill", base_price=2500, unit="per unit"),
            ServiceItem(category_id=cat_plumb.id, name="Tap Leak Repair", base_price=300, unit="per job"),
            ServiceItem(category_id=cat_plumb.id, name="Commode Installation", base_price=1200, unit="per unit"),
            ServiceItem(category_id=cat_elec.id, name="Fan Installation", base_price=400, unit="per unit"),
            ServiceItem(category_id=cat_elec.id, name="Whole House Wiring Check", base_price=1000, unit="per visit")
        ]
        
        db.add_all(items)
        db.commit()
        print("Successfully seeded categories and items!")
    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_services()
