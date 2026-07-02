import sqlite3

def check_my_tables():
    conn = sqlite3.connect("blockflow.db")
    cursor = conn.cursor()
    
    # 1. Check Sales
    print("\n--- 📈 RECORDED SALES ---")
    try:
        cursor.execute("SELECT * FROM sales")
        sales = cursor.fetchall()
        for row in sales:
            print(f"ID: {row[0]} | Customer: {row[1]} | Shop: {row[2]} | Size: {row[3]} | Qty: {row[4]} | Date: {row[5]}")
    except sqlite3.OperationalError:
        print("Sales table does not exist yet.")

    # 2. Check Inventory
    print("\n--- 🧱 RECORDED INVENTORY STOCK ---")
    try:
        cursor.execute("SELECT * FROM inventory")
        stocks = cursor.fetchall()
        for row in stocks:
            print(f"ID: {row[0]} | Item: {row[1]} | Size: {row[2]} | Qty: {row[3]} {row[4]}")
    except sqlite3.OperationalError:
        print("Inventory table does not exist yet.")

    conn.close()

if __name__ == "__main__":
    check_my_tables()