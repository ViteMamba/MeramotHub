from app.database import engine, Base
from app.models.user import User
from app.models.service_provider import ServiceProviderProfile
from app.models.service import ServiceCategory, ServiceItem

def reset_tables():
    print("Dropping and recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Tables reset successfully!")

if __name__ == "__main__":
    reset_tables()
