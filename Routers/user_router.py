from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import (
    record_expense, 
    record_new_stock, 
    record_sale, 
    get_transaction_history,
    register_user,      
    verify_user_login   
)

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
        # Return the list directly so the frontend is able to parse it without failing the `isinstance` check!
        return get_transaction_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))