"""
Add missing columns and tables for Phase 2 features.
Safe to run multiple times (idempotent).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from sqlalchemy import text, inspect

# Import all models so their metadata is registered
from app.models import *  # noqa

def run_migration():
    inspector = inspect(engine)

    with engine.connect() as conn:
        # 1. Create messages table if it doesn't exist
        if not inspector.has_table("messages"):
            print("Creating 'messages' table...")
            Base.metadata.tables["messages"].create(engine)
            print("  Done.")
        else:
            print("'messages' table already exists.")

        # 2. Add resolution_note column to complaints if missing
        if inspector.has_table("complaints"):
            columns = [c["name"] for c in inspector.get_columns("complaints")]
            if "resolution_note" not in columns:
                print("Adding 'resolution_note' column to complaints...")
                conn.execute(text("ALTER TABLE complaints ADD COLUMN resolution_note TEXT;"))
                conn.commit()
                print("  Done.")
            else:
                print("'resolution_note' column already exists in complaints.")
        
        print("\nMigration complete!")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
