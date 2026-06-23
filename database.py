import sqlite3

def get_db_connection():
    # Connects to a local file database right inside your project folder
    conn = sqlite3.connect("blockflow.db")
    # This configuration makes SQLite return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn

import sqlite3

def add_expense_to_db(category: str, description: str, amount: float, date_recorded: str):
    conn = sqlite3.connect("blockflow.db")
    cursor = conn.cursor()
    
    # Creates the table automatically if it doesn't exist yet
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date_recorded TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        INSERT INTO expenses (category, description, amount, date_recorded)
        VALUES (?, ?, ?, ?)
    """, (category, description, amount, date_recorded))
    
    conn.commit()
    conn.close()
    return True