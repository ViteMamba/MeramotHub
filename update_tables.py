from app.database import engine, Base
from app.models.user import User
from app.models.service_provider import ServiceProviderProfile
from app.models.service import ServiceCategory, ServiceItem

def create_tables():
    print("Updating database tables for Page 4...")
    Base.metadata.create_all(bind=engine)
    print("Tables updated successfully!")

if __name__ == "__main__":
    create_tables()
