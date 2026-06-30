# init_db.py
import sqlite3
import hashlib

def initialize():
    conn = sqlite3.connect("blockflow.db")
    cursor = conn.cursor()
    
    # 1. Create the table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)
    
    # Generate the SHA-256 password hash for Admin123
    hashed_password = hashlib.sha256("Admin123".encode('utf-8')).hexdigest()
    
    # 2. Insert Owner and Client accounts safely
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
        print("Database initialized and mock accounts inserted successfully!")
    except sqlite3.IntegrityError:
        print("Database already initialized with users.")
    finally:
        conn.close()

if __name__ == "__main__":
    initialize()