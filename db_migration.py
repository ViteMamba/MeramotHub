import sys
import os

# Ensure the parent directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def run_migration():
    print("Connecting to the database...")
    with engine.connect() as conn:
        print("Executing SQL query...")
        conn.execute(text("ALTER TABLE payments ALTER COLUMN provider_id DROP NOT NULL;"))
        conn.commit()
        print("Successfully dropped NOT NULL constraint on payments.provider_id!")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"Error executing migration: {e}")
        sys.exit(1)
