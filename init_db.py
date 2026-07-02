import sqlite3
import hashlib

def initialize():
    # Connects directly to your local file system database instance
    conn = sqlite3.connect("blockflow.db")
    cursor = conn.cursor()
    
    # 1. Create the Users Authentication Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)
    
    # 2. Create the Inventory / Stock Recording Table 
    # Perfectly fits your item name, structural size variations, total quantity, and core units!
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
    
    # Generate the SHA-256 password hash signature for standard credentials
    hashed_password = hashlib.sha256("Admin123".encode('utf-8')).hexdigest()
    
    # 3. Safely populate system administrative roles
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