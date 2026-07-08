from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import record_expense, record_new_stock, record_sale, get_transaction_history

router = APIRouter()

# --- ORIGINAL BUSINESS SCHEMAS ---

class ExpenseRequest(BaseModel):
    expense_name: str
    amount: float
    category: str
    date_added: str

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

class LoginRequest(BaseModel):
    username: str
    password: str

# --- ROUTE ENDPOINTS ---

@router.post("/login")
def login(data: LoginRequest):
    if data.username == "admin" and data.password == "password":
        return {"status": "success", "message": "Logged in successfully"}
    raise HTTPException(status_code=400, detail="Invalid credentials")

@router.post("/register")
def register():
    return {"status": "success", "message": "User registration endpoint shell"}

@router.post("/expenses")
def add_expense(data: ExpenseRequest):
    try:
        record_expense(data.expense_name, data.amount, data.category, data.date_added)
        return {"status": "success", "message": "Expense transaction saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inventory")
def add_inventory(data: InventoryRequest):
    try:
        record_new_stock(data.item_name, data.quantity, data.price, data.date_added)
        return {"status": "success", "message": "Inventory restock tracked!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sales")
def add_sale(data: SalesRequest):
    try:
        record_sale(
            data.customer_name, 
            data.shop_name, 
            data.block_size, 
            data.quantity, 
            data.sale_date
        )
        return {"status": "success", "message": "Sale logged successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def view_transaction_history():
    try:
        data = get_transaction_history()
        return {"status": "success", "history": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))