import sqlite3

def get_db_connection():
    conn = sqlite3.connect("blockflow.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- SYSTEM INTEGRITY CHECK ---
def ensure_schema_integrity():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Dashboard timeline tracker
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            type TEXT,
            date_record TEXT
        )
    """)
    
    # 2. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)

    # 3. Inventory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            quantity INTEGER,
            size TEXT DEFAULT 'None',
            unit TEXT DEFAULT 'pcs',
            price REAL DEFAULT 0.0,
            date_added TEXT,
            date_recorded TEXT
        )
    """)

    # --- AUTO-MIGRATIONS FOR INVENTORY ---
    cursor.execute("PRAGMA table_info(inventory)")
    inv_columns = [row[1] for row in cursor.fetchall()]
    
    migrations = {
        "price": "REAL DEFAULT 0.0",
        "date_added": "TEXT",
        "date_recorded": "TEXT",
        "size": "TEXT DEFAULT 'None'",
        "unit": "TEXT DEFAULT 'pcs'"
    }
    
    for col_name, col_type in migrations.items():
        if col_name not in inv_columns:
            try:
                cursor.execute(f"ALTER TABLE inventory ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass
    
    conn.commit()
    conn.close()

ensure_schema_integrity()

# --- RECORD NEW STOCK ---
def record_new_stock(item_name, quantity, price, date_added, size="None", unit="pcs"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(inventory)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Robust string cleaning for dropdown sizes (e.g., "L (Large) - ₱7/pc" -> "L")
    clean_size = "None"
    if size is not None:
        size_str = str(size).strip()
        if size_str and size_str.lower() != "none":
            if "XL" in size_str:
                clean_size = "XL"
            elif "L" in size_str:
                clean_size = "L"
            else:
                clean_size = size_str.split(" - ")[0].strip()

    insert_cols = ["item_name", "quantity"]
    insert_vals = [item_name, int(quantity or 0)]
    
    # Fill standard structural columns dynamically
    if "price" in existing_columns:
        insert_cols.append("price")
        insert_vals.append(float(price or 0.0))
        
    if "date_added" in existing_columns:
        insert_cols.append("date_added")
        insert_vals.append(date_added)

    if "date_recorded" in existing_columns:
        insert_cols.append("date_recorded")
        insert_vals.append(date_added)

    if "size" in existing_columns:
        insert_cols.append("size")
        insert_vals.append(clean_size)

    if "unit" in existing_columns:
        insert_cols.append("unit")
        insert_vals.append(str(unit).strip() if unit else "pcs")
        
    placeholders = ", ".join(["?"] * len(insert_vals))
    col_names = ", ".join(insert_cols)
    
    query = f"INSERT INTO inventory ({col_names}) VALUES ({placeholders})"
    cursor.execute(query, tuple(insert_vals))
    
    # Stock is an asset addition, we keep it positive to prevent it from reducing your profit metrics as a red negative
    total_cost = float(price or 0.0) * int(quantity or 0)
    
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, 'inventory', ?)",
        (f"Stocked: {item_name}", total_cost, date_added)
    )
    
    conn.commit()
    conn.close()

# --- CLEAN RECONCILED TRANSACTION HISTORY ---
def get_transaction_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    history = []
    
    try:
        # Pull cleanly from dashboard records only to eliminate all duplication across views
        query = """
            SELECT id, title, amount, type, date_record 
            FROM dashboard 
            ORDER BY date_record DESC, id DESC
        """
        cursor.execute(query)
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
    history.sort(key=lambda x: x['date'] if x['date'] else "", reverse=True)
    return history

def record_expense(expense_name, amount, category, date_added):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(expenses)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    insert_cols = []
    insert_vals = []
    
    if "expense_name" in existing_columns:
        insert_cols.append("expense_name")
        insert_vals.append(expense_name)
    if "description" in existing_columns:
        insert_cols.append("description")
        insert_vals.append(expense_name)
        
    if "date_added" in existing_columns:
        insert_cols.append("date_added")
        insert_vals.append(date_added)
    if "date_recorded" in existing_columns:
        insert_cols.append("date_recorded")
        insert_vals.append(date_added)
        
    if "amount" in existing_columns:
        insert_cols.append("amount")
        insert_vals.append(amount)
    if "category" in existing_columns:
        insert_cols.append("category")
        insert_vals.append(category)

    if insert_cols:
        placeholders = ", ".join(["?"] * len(insert_vals))
        col_names = ", ".join(insert_cols)
        query = f"INSERT INTO expenses ({col_names}) VALUES ({placeholders})"
        cursor.execute(query, tuple(insert_vals))
    
    # Expenses are marked negative so they are mathematically subtracted from profit calculations
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, 'expense', ?)",
        (expense_name, -amount, date_added)
    )
    
    conn.commit()
    conn.close()

def record_sale(customer_name, shop_name, block_size, quantity, sale_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO sales (customer_name, shop_name, block_size, quantity, sale_date) VALUES (?, ?, ?, ?, ?)",
        (customer_name, shop_name, block_size, quantity, sale_date)
    )
    
    price_per_pc = 7.0
    if "7" in block_size:
        price_per_pc = 7.0
    elif "6" in block_size:
        price_per_pc = 6.0
    elif "5" in block_size:
        price_per_pc = 5.0
        
    total_amount = float(quantity) * price_per_pc
    clean_size = block_size.strip()
    sale_title = f"{clean_size} x{quantity} - {customer_name} ({shop_name})"
    
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, 'sale', ?)",
        (sale_title, total_amount, sale_date)
    )
    
    conn.commit()
    conn.close()

def register_user(email, password, role):
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    cursor.execute("SELECT role FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"status": "success", "role": user["role"]}
    return None