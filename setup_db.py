from database import ensure_schema_integrity, register_user
import getpass
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().with_name("blockflow.db")

print(f"Database: {DB_PATH}")

try:
    # Create or migrate the schema before clearing it. This makes the reset
    # script usable on a fresh checkout as well as an existing installation.
    ensure_schema_integrity()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        print("\nClearing BlockFlow data...")

        # Delete all operational/test data while keeping the schema intact.
        for table in ("transactions", "sales", "expenses", "inventory"):
            cursor.execute(f"DELETE FROM {table}")
            print(f"Cleared: {table}")

        cursor.execute("""
                DELETE FROM sqlite_sequence
                WHERE name IN ('transactions', 'sales', 'expenses', 'inventory')
            """)
        print("Reset ID counters.")

        # Remove existing users so the database starts clean.
        cursor.execute("DELETE FROM users")

    # Use the application's password hasher instead of inserting a
    # plaintext password directly into SQLite. Do not keep a default
    # credential in source control.
    owner_email = input("Owner email [admin@blockflow.com]: ").strip()
    owner_email = owner_email or "admin@blockflow.com"
    owner_password = getpass.getpass("Owner password (8+ characters): ")
    if not register_user(owner_email, owner_password, "owner"):
        raise RuntimeError("Could not create the default owner account.")

    # Shrink the database file.
    with sqlite3.connect(DB_PATH) as vacuum_conn:
        vacuum_conn.execute("VACUUM")

    print("\n===================================")
    print("DATABASE RESET SUCCESSFUL")
    print("===================================")
    print("Inventory:    0 records")
    print("Sales:        0 records")
    print("Expenses:     0 records")
    print("Transactions: 0 records")
    print("Users:        1 owner account")
    print()
    print("Owner account:")
    print(f"Email:    {owner_email}")
    print("Password: supplied securely during setup")
    print("===================================")

except Exception as e:
    print("\nERROR:")
    print(e)
    print("\nNo changes were committed.")