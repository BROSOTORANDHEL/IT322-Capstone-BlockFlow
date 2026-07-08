import sqlite3

def get_db_connection():
    conn = sqlite3.connect("blockflow.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- DUAL-TABLE AUTOMATION FUNCTIONS ---

def record_expense(expense_name, amount, category, date_added):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO expenses (expense_name, amount, category, date_added) VALUES (?, ?, ?, ?)",
        (expense_name, amount, category, date_added)
    )
    
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, 'expense', ?)",
        (expense_name, amount, date_added)
    )
    
    conn.commit()
    conn.close()

def record_new_stock(item_name, quantity, price, date_added):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO inventory (item_name, quantity, price, date_added) VALUES (?, ?, ?, ?)",
        (item_name, quantity, price, date_added)
    )
    
    total_cost = float(price) * int(quantity)
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, 'inventory', ?)",
        (f"Stocked: {item_name}", total_cost, date_added)
    )
    
    conn.commit()
    conn.close()

def record_sale(customer_name, shop_name, block_size, quantity, sale_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Keeping your custom sales data format completely intact
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            customer_name TEXT,
            shop_name TEXT,
            block_size TEXT,
            quantity INTEGER,
            sale_date TEXT
        )
    """)
    
    cursor.execute(
        "INSERT INTO sales (customer_name, shop_name, block_size, quantity, sale_date) VALUES (?, ?, ?, ?, ?)",
        (customer_name, shop_name, block_size, quantity, sale_date)
    )
    
    # Syncing transaction detail straight to your timeline log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            type TEXT,
            date_record TEXT
        )
    """)
    
    # FIX: Matching exactly 4 placeholders (?) with 4 variable inputs
    sale_title = f"{block_size} x{quantity} - {customer_name} ({shop_name})"
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, ?, ?)",
        (sale_title, float(quantity), 'sale', sale_date)
    )
    
    conn.commit()
    conn.close()

# --- UNIFIED TRANSACTION HISTORY LOG ---

def get_transaction_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    history = []
    
    # 1. Fetch from master dashboard log table
    try:
        cursor.execute("SELECT id, title, amount, type, date_record FROM dashboard ORDER BY id DESC")
        for row in cursor.fetchall():
            history.append({
                "id": row["id"],
                "title": row["title"],
                "amount": row["amount"],
                "type": row["type"],
                "date": row["date_record"]
            })
    except sqlite3.OperationalError:
        pass

    # 2. SAFETY NET: Automatically scan existing past sales records if dashboard log is blank
    try:
        cursor.execute("SELECT rowid, customer_name, shop_name, block_size, quantity, sale_date FROM sales")
        for row in cursor.fetchall():
            sale_title = f"{row['block_size']} x{row['quantity']} - {row['customer_name']} ({row['shop_name']})"
            
            # Prevent duplicates if they match title and date
            already_tracked = any(item["title"] == sale_title and item["date"] == row["sale_date"] for item in history)
            
            if not already_tracked:
                history.append({
                    "id": row["rowid"],
                    "title": sale_title,
                    "amount": float(row["quantity"]),
                    "type": "sale",
                    "date": row["sale_date"]
                })
    except sqlite3.OperationalError:
        pass
        
    conn.close()
    
    # Sort chronologically, newest entries first
    history.sort(key=lambda x: x['date'] if x['date'] else "", reverse=True)
    return history