from fastapi import APIRouter, HTTPException
from Handlers.user_handler import login_handler
from Models.user_model import ExpenseSchema
from pydantic import BaseModel
from database import add_expense_to_db
import sqlite3
import hashlib

router = APIRouter()

class UserAuthSchema(BaseModel):
    email: str
    password: str

# Existing login connection endpoint route
router.post("/login")(login_handler)

# Registration Route using your correct SHA-256 Hashing and Roles
@router.post("/register", status_code=201)
def register_user(user_data: UserAuthSchema): 
    """
    Registers a brand-new user account using SHA-256 security guidelines.
    """
    try:
        conn = sqlite3.connect("blockflow.db")
        cursor = conn.cursor()
        
        # Hash the incoming plain-text password to match your database standard!
        hashed = hashlib.sha256(user_data.password.encode('utf-8')).hexdigest()
        
        # Inject with a default role of 'client' to satisfy your NOT NULL constraint
        cursor.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
            (user_data.email, hashed, "client")
        )
        conn.commit()
        return {"status": "success", "message": "User registered successfully!"}
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User account already exists.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# Existing transactions endpoint route
@router.post("/expenses", status_code=201)
def record_expense(expense_data: ExpenseSchema):
    try:
        success = add_expense_to_db(
            title=expense_data.title,
            category=expense_data.category,
            description=expense_data.description,
            amount=expense_data.amount,
            date_recorded=expense_data.date_recorded
        )
        if success:
            return {"status": "success", "message": "Expense entry logged successfully!"}
        else:
            raise HTTPException(status_code=400, detail="Failed to save expense entry.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))