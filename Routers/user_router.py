from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import (
    get_db_connection,  # Imported to retrieve records for the GET endpoint
    record_expense, 
    record_new_stock, 
    record_sale, 
    get_transaction_history,
    register_user,      
    verify_user_login   
)
import sqlite3

# If your main App.py mounts this router with: app.include_router(router, prefix="/api")
# then these endpoints will be accessed as "/api/login", "/api/expenses", etc.
router = APIRouter()

# --- BUSINESS SCHEMAS ---

class ExpenseRequest(BaseModel):
    expense_name: str  # Maps to 'expense_name' sent by your frontend form
    amount: float      # Pure float sent by your frontend form
    category: str      # Selected from dropdown
    date_added: str    # YYYY-MM-DD string format

class InventoryRequest(BaseModel):
    item_name: str
    quantity: int
    price: float
    date_added: str

class SalesRequest(BaseModel):
    customer_name: str
    shop_name: str
    block_size: str
    quantity: int
    sale_date: str

# --- AUTHENTICATION SCHEMAS ---

class LoginRequest(BaseModel):
    email: str  
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str

# --- ROUTE ENDPOINTS ---

@router.post("/login")
def login(data: LoginRequest):
    user_match = verify_user_login(data.email, data.password)
    if user_match:
        return {
            "status": "success", 
            "message": "Logged in successfully", 
            "role": user_match["role"]
        }
    raise HTTPException(status_code=400, detail="Invalid email or password credentials")

@router.post("/register")
def register(data: RegisterRequest):
    success = register_user(data.email, data.password, data.role)
    if not success:
        raise HTTPException(status_code=400, detail="This email is already registered!")
    return {"status": "success", "message": "Account created successfully!"}


# GET /api/expenses
# This endpoint dynamically pulls your live SQLite table data to keep the frontend updated!
@router.get("/expenses")
def get_expenses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # CORRECTED: execute PRAGMA as standard SQL
        cursor.execute("PRAGMA table_info(expenses)")
        columns = [row["name"] for row in cursor.fetchall()]
        
        # Pull all saved rows from your database
        cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
        rows = cursor.fetchall()
        
        expenses_list = []
        for row in rows:
            # Map description/expense_name depending on actual table structure
            desc_val = row["description"] if "description" in columns else row.get("expense_name", "")
            
            # Map date_recorded/date_added depending on actual table structure
            date_val = row["date_recorded"] if "date_recorded" in columns else row.get("date_added", "")
            
            expenses_list.append({
                "id": row["id"],
                "category": row["category"],
                "description": desc_val,
                "expense_name": desc_val, # Fallback mapping
                "amount": row["amount"],
                "date_recorded": date_val,
                "date_added": date_val      # Fallback mapping
            })
            
        conn.close()
        return expenses_list
        
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database operational error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# POST /api/expenses
@router.post("/expenses")
def add_expense(data: ExpenseRequest):
    try:
        # Executes record_expense with validated fields perfectly matching database types
        record_expense(
            expense_name=data.expense_name, 
            amount=data.amount, 
            category=data.category, 
            date_added=data.date_added
        )
        return {"status": "success", "message": "Expense transaction saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inventory")
def add_inventory(data: InventoryRequest):
    try:
        record_new_stock(item_name=data.item_name, quantity=data.quantity, price=data.price, date_added=data.date_added)
        return {"status": "success", "message": "Inventory restock tracked!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sales")
def add_sale(data: SalesRequest):
    try:
        record_sale(
            customer_name=data.customer_name, 
            shop_name=data.shop_name, 
            block_size=data.block_size, 
            quantity=data.quantity, 
            sale_date=data.sale_date
        )
        return {"status": "success", "message": "Sale logged successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def view_transaction_history():
    try:
        # Return the list directly so the frontend is able to parse it without failing!
        return get_transaction_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))