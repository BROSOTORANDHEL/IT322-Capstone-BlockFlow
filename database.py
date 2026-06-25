import sqlite3

def get_db_connection():
    # Connects to a local file database right inside your project folder
    conn = sqlite3.connect("blockflow.db")
    # This configuration makes SQLite return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn

