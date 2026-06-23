from fastapi import APIRouter
from Handlers.user_handler import login_handler

router = APIRouter()

router.post("/login")(login_handler)

from Models.user_model import ExpenseSchema
from database import add_expense_to_db

@router.post("/expenses", status_code=201)
def record_expense(expense_data: ExpenseSchema):
    try:
        success = add_expense_to_db(
            category=expense_data.category,
            description=expense_data.description,
            amount=expense_data.amount,
            date_recorded=expense_data.date_recorded
        )
        if success:
            return {"status": "success", "message": "Expense entry logged successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))