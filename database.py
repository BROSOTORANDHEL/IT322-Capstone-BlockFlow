import sqlite3

def get_db_connection():
    conn = sqlite3.connect("blockflow.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- DUAL-TABLE AUTOMATION FUNCTIONS ---

def record_expense(expense_name, amount, category, date_added):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            type TEXT,
            date_record TEXT
        )
    """)
    
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            type TEXT,
            date_record TEXT
        )
    """)
    
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            type TEXT,
            date_record TEXT
        )
    """)
    
    # 1. Parse out the price per piece from the block size (e.g., "L (Large) - ₱7/pc")
    price_per_pc = 7.0
    if "7" in block_size:
        price_per_pc = 7.0
    elif "6" in block_size:
        price_per_pc = 6.0
    elif "5" in block_size:
        price_per_pc = 5.0
        
    total_amount = float(quantity) * price_per_pc
    
    # 2. Build the title EXACTLY like your working mock data format:
    # "L (Large) - ₱7/pc x1200 - Juan Dela Cruz (ABC Construction Supply)"
    clean_size = block_size.strip()
    sale_title = f"{clean_size} x{quantity} - {customer_name} ({shop_name})"
    
    # 3. Write to the dashboard table with the full cash amount (not just quantity!)
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, 'sale', ?)",
        (sale_title, total_amount, sale_date)
    )
    
    conn.commit()
    conn.close()

# --- UNIFIED TRANSACTION HISTORY LOG ---

def get_transaction_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    history = []
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            type TEXT,
            date_record TEXT
        )
    """)
    
    try:
        # Fetch directly from dashboard - this matches your UI parser exactly!
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

    conn.close()
    
    # Sort history records by date (newest first)
    history.sort(key=lambda x: x['date'] if x['date'] else "", reverse=True)
    return history


# --- USER AUTHENTICATION HELPERS ---

def register_user(email, password, role):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)
    
    cursor.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return False 

    cursor.execute(
        "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
        (email, password, role)
    )
    conn.commit()
    conn.close()
    return True

def verify_user_login(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)
    
    cursor.execute("SELECT role FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"status": "success", "role": user["role"]}
    return None