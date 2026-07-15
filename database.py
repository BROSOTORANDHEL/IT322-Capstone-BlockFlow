import sqlite3

def get_db_connection():
    conn = sqlite3.connect("blockflow.db")
    conn.row_factory = sqlite3.Row
    return conn

# --- SYSTEM INTEGRITY CHECK ---
def ensure_schema_integrity():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure dashboard table exists for UI timeline tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            type TEXT,
            date_record TEXT
        )
    """)
    
    # Ensure standard user table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    """)
    
    conn.commit()
    conn.close()

ensure_schema_integrity()

# --- ADAPTIVE EXPENSE RECORDING ---
def record_expense(expense_name, amount, category, date_added):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Query the actual columns currently present in your local 'expenses' database table
    cursor.execute("PRAGMA table_info(expenses)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    insert_cols = []
    insert_vals = []
    
    # 2. Map payload dynamically to match whatever columns exist in your schema
    
    # Map Description fields (satisfies NOT NULL constraint if 'description' is present)
    if "expense_name" in existing_columns:
        insert_cols.append("expense_name")
        insert_vals.append(expense_name)
    if "description" in existing_columns:
        insert_cols.append("description")
        insert_vals.append(expense_name)
        
    # Map Date fields (satisfies NOT NULL constraint if 'date_recorded' is present)
    if "date_added" in existing_columns:
        insert_cols.append("date_added")
        insert_vals.append(date_added)
    if "date_recorded" in existing_columns:
        insert_cols.append("date_recorded")
        insert_vals.append(date_added)
        
    # Map Amount & Category
    if "amount" in existing_columns:
        insert_cols.append("amount")
        insert_vals.append(amount)
    if "category" in existing_columns:
        insert_cols.append("category")
        insert_vals.append(category)

    # 3. Build dynamic insert query matching local table schema
    if insert_cols:
        placeholders = ", ".join(["?"] * len(insert_vals))
        col_names = ", ".join(insert_cols)
        query = f"INSERT INTO expenses ({col_names}) VALUES ({placeholders})"
        cursor.execute(query, tuple(insert_vals))
    
    # 4. Save to dashboard system for Admin tracking
    cursor.execute(
        "INSERT INTO dashboard (title, amount, type, date_record) VALUES (?, ?, 'expense', ?)",
        (expense_name, amount, date_added)
    )
    
    conn.commit()
    conn.close()

# --- OTHER OPERATIONS ---

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

# --- RECONCILED ADMIN TRANSACTION HISTORY ---
def get_transaction_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    history = []
    
    try:
        # Dynamically inspect columns in expenses table
        cursor.execute("PRAGMA table_info(expenses)")
        exp_cols = [row[1] for row in cursor.fetchall()]
        
        # Map dynamic description and date fields for the expenses portion
        desc_col = "description" if "description" in exp_cols else ("expense_name" if "expense_name" in exp_cols else "''")
        date_col = "date_recorded" if "date_recorded" in exp_cols else ("date_added" if "date_added" in exp_cols else "''")
        
        # SQL Union: Combines dashboard table entries AND raw expenses table entries 
        # (Using a subquery with DISTINCT to prevent duplicate rendering of the same transaction)
        query = f"""
            SELECT DISTINCT id, title, amount, type, date_record FROM (
                SELECT id, title, amount, type, date_record FROM dashboard
                UNION ALL
                SELECT id, {desc_col} AS title, amount, 'expense' AS type, {date_col} AS date_record FROM expenses
            ) AS combined_history
            GROUP BY title, amount, date_record  -- Prevents showing duplicates logged in both tables
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
        # If any join tables don't exist yet, fallback gracefully to base dashboard
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

    conn.close()
    
    history.sort(key=lambda x: x['date'] if x['date'] else "", reverse=True)
    return history

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