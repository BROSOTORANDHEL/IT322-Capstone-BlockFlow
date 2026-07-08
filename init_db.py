import sqlite3
import hashlib

def initialize():
    conn = sqlite3.connect("blockflow.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        size TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit TEXT NOT NULL,
        date_recorded TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    hashed_password = hashlib.sha256("Admin123".encode('utf-8')).hexdigest()
    
    try:
        cursor.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
            ("BlockFlow@user.com", hashed_password, "owner")
        )
        cursor.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
            ("client@user.com", hashed_password, "client")
        )
        conn.commit()
        print("🟢 Database initialized successfully! Core users and stock recording schemas are live.")
    except sqlite3.IntegrityError:
        print("ℹ️ Database records already contain seeded structural users. Inventory schema confirmed.")
    finally:
        conn.close()

if __name__ == "__main__":
    initialize()