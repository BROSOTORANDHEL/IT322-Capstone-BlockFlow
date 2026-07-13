import sqlite3

conn = sqlite3.connect("blockflow.db")
cursor = conn.cursor()

# Creates the users table with a role tracker column
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# Optional: Add a default admin account for your first login test
try:
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("Admin", "Admin123", "Admin / Owner"))
    conn.commit()
    print("Default admin account created: Admin / Admin123")
except sqlite3.IntegrityError:
    pass # Account already exists

conn.close()