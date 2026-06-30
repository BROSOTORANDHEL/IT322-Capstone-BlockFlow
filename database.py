import sqlite3

def get_db_connection():
    """
    Connects to a local file database right inside your project folder
    """
    conn = sqlite3.connect("blockflow.db")
    # This configuration makes SQLite return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn

def add_expense_to_db(title, category, description, amount, date_recorded):
    """
    Inserts a newly recorded expense entry into blockflow.db
    """
    try:
        conn = sqlite3.connect("blockflow.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO expenses (title, category, description, amount, date_recorded)
            VALUES (?, ?, ?, ?, ?)
        """, (title, category, description, amount, date_recorded))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Database Error inside add_expense_to_db: {e}")
        return False
    finally:
        conn.close()