from app.database import engine
from sqlalchemy import text

def force_drop():
    print("Force dropping tables with CASCADE...")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS users, service_provider_profiles, service_categories, service_items, bookings, payments, reviews, complaints, subscriptions CASCADE"))
        conn.commit()
    print("Done.")

if __name__ == "__main__":
    force_drop()
