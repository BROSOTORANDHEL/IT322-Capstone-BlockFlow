import sqlite3

def get_db_connection():
    """
    Connects to the local file database right inside your project folder.
    Configured to return rows as dictionary-like objects.
    """
    conn = sqlite3.connect("blockflow.db")
    conn.row_factory = sqlite3.Row
    return conn

# =====================================================================
# INVENTORY / STOCK FUNCTIONS
# =====================================================================

def add_stock_to_db(item_name: str, size: str, quantity: int, unit: str):
    """
    Inserts a newly recorded inventory/stock entry into blockflow.db.
    Matches your Figma Record New Stock UI modal data perfectly!
    """
    try:
        conn = sqlite3.connect("blockflow.db")
        cursor = conn.cursor()
        
        # Ensure table exists with parameters matching your UI
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                size TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit TEXT NOT NULL,
                date_recorded TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO inventory (item_name, size, quantity, unit)
            VALUES (?, ?, ?, ?)
        """, (item_name, size, int(quantity), unit))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Database Error inside add_stock_to_db: {e}")
        return False
    finally:
        conn.close()

# =====================================================================
# EXPENSE FUNCTIONS (Dual-Table Automation)
# =====================================================================

def add_expense_to_db(category: str, description: str, amount: float, date_recorded: str):
    """
    Safely creates the expenses table and inserts a 4-argument expense entry,
    while simultaneously generating a dedicated dashboard analytics table
    storing exclusively the amount and automatic timestamps.
    """
    try:
        conn = sqlite3.connect("blockflow.db")
        cursor = conn.cursor()
        
        # Table 1: Complete comprehensive expense ledger
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                date_recorded TEXT NOT NULL,
                date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 2: Simplified dashboard specific table tracking ONLY transaction costs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert 1: Push full details into your master list
        cursor.execute("""
            INSERT INTO expenses (category, description, amount, date_recorded)
            VALUES (?, ?, ?, ?)
        """, (category, description, amount, date_recorded))
        
        # Insert 2: Extract and push ONLY the numerical cost metric to the dashboard table
        cursor.execute("""
            INSERT INTO dashboard_expenses (amount)
            VALUES (?)
        """, (amount,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Database Error inside dual-insert add_expense_to_db: {e}")
        return False
    finally:
        conn.close()

# =====================================================================
# SALES FUNCTIONS
# =====================================================================

def add_sale_to_db(customer_name: str, shop_name: str, block_size: str, quantity: int, sale_date: str):
    """
    Inserts a newly recorded sales transaction into blockflow.db.
    Matches the Figma Record Sale modal dataset perfectly!
    """
    try:
        conn = sqlite3.connect("blockflow.db")
        cursor = conn.cursor()
        
        # Ensure the sales table matches your UI fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                shop_name TEXT NOT NULL,
                block_size TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                sale_date TEXT NOT NULL,
                date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO sales (customer_name, shop_name, block_size, quantity, sale_date)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_name, shop_name, block_size, int(quantity), sale_date))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Database Error inside add_sale_to_db: {e}")
        return False
    finally:
        conn.close()