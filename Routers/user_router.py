from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import (
    get_db_connection,
    record_expense,
    record_new_stock,
    record_sale,
    get_transaction_history,
    register_user,
    verify_user_login
)
import sqlite3

router = APIRouter()


# -----------------------------
# REQUEST MODELS
# -----------------------------

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
    size: str
    unit: str


class SalesRequest(BaseModel):
    customer_name: str
    shop_name: str
    block_size: str
    quantity: int
    sale_date: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str


# -----------------------------
# AUTH
# -----------------------------

@router.post("/login")
def login(data: LoginRequest):
    user_match = verify_user_login(data.email, data.password)

    if user_match:
        return {
            "status": "success",
            "message": "Logged in successfully",
            "role": user_match["role"]
        }

    raise HTTPException(
        status_code=400,
        detail="Invalid email or password credentials"
    )


@router.post("/register")
def register(data: RegisterRequest):
    success = register_user(
        data.email,
        data.password,
        data.role
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="This email is already registered!"
        )

    return {
        "status": "success",
        "message": "Account created successfully!"
    }


# -----------------------------
# EXPENSES
# -----------------------------

@router.get("/expenses")
def get_expenses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(expenses)")
        columns = [row["name"] for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
        rows = cursor.fetchall()

        expenses = []

        for row in rows:

            description = (
                row["description"]
                if "description" in columns
                else row["expense_name"]
            )

            date_value = (
                row["date_recorded"]
                if "date_recorded" in columns
                else row["date_added"]
            )

            expenses.append({
                "id": row["id"],
                "expense_name": description,
                "description": description,
                "category": row["category"],
                "amount": row["amount"],
                "date_added": date_value,
                "date_recorded": date_value
            })

        conn.close()
        return expenses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expenses")
def add_expense(data: ExpenseRequest):
    try:

        record_expense(
            expense_name=data.expense_name,
            amount=data.amount,
            category=data.category,
            date_added=data.date_added
        )

        return {
            "status": "success",
            "message": "Expense transaction saved!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# INVENTORY
# -----------------------------

@router.get("/inventory")
def get_inventory():
    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                item_name,
                size,
                quantity,
                unit,
                price,
                date_added,
                date_recorded
            FROM inventory
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        inventory = []

        for row in rows:
            inventory.append({
                "id": row["id"],
                "item_name": row["item_name"],
                "size": row["size"],
                "quantity": row["quantity"],
                "unit": row["unit"],
                "price": row["price"],
                "date_added": row["date_added"],
                "date_recorded": row["date_recorded"]
            })

        conn.close()

        return inventory

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inventory")
def add_inventory(data: InventoryRequest):
    try:

        record_new_stock(
            item_name=data.item_name,
            quantity=data.quantity,
            price=data.price,
            date_added=data.date_added,
            size=data.size,
            unit=data.unit
        )

        return {
            "status": "success",
            "message": "Inventory restock tracked!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# SALES
# -----------------------------

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

        return {
            "status": "success",
            "message": "Sale logged successfully!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# HISTORY
# -----------------------------

@router.get("/history")
def view_transaction_history():
    try:
        return get_transaction_history()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))