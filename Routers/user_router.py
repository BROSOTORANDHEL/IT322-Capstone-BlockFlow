from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Handlers.user_handler import login_handler
from database import add_expense_to_db, add_stock_to_db, add_sale_to_db
from database import add_expense_to_db, add_stock_to_db

router = APIRouter()

# =====================================================================
# REQUEST SCHEMAS (Validation Layouts)
# =====================================================================

class ExpenseSchema(BaseModel):
    category: str
    description: str
    amount: float
    date_recorded: str

class InventoryStockSchema(BaseModel):
    item_name: str
    size: str
    quantity: int
    unit: str

class SaleSchema(BaseModel):
    customer_name: str
    shop_name: str
    block_size: str
    quantity: int
    sale_date: str

# =====================================================================
# ENDPOINTS
# =====================================================================

# 1. User Authentication
router.post("/login")(login_handler)


# 1. User Authentication
router.post("/login")(login_handler)

# 2. Record New Business Expense
@router.post("/expenses", status_code=201)
def record_expense(expense_data: ExpenseSchema):
    """
    API endpoint to log business expenses using 4-argument mapping.
    """
    try:
        success = add_expense_to_db(
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

# 3. Record New Stock (Inventory Management from your Figma mockup)
@router.post("/inventory", status_code=201)
def record_new_stock(stock_data: InventoryStockSchema):
    """
    API endpoint that receives incoming stock creation data from the client form modal.
    """
    try:
        success = add_stock_to_db(
            item_name=stock_data.item_name,
            size=stock_data.size,
            quantity=stock_data.quantity,
            unit=stock_data.unit
        )
        if success:
            return {"status": "success", "message": f"{stock_data.item_name} stock logged successfully!"}
        else:
            raise HTTPException(status_code=400, detail="Failed to log new inventory stock.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. Record New Sale (Sales Tracking from your Figma mockup)
@router.post("/sales", status_code=201)
def record_sale(sale_data: SaleSchema):
    """
    API endpoint that receives sales transaction submissions from the frontend modal.
    """
    try:
        success = add_sale_to_db(
            customer_name=sale_data.customer_name,
            shop_name=sale_data.shop_name,
            block_size=sale_data.block_size,
            quantity=sale_data.quantity,
            sale_date=sale_data.sale_date
        )
        if success:
            return {"status": "success", "message": f"Sale for {sale_data.customer_name} recorded successfully!"}
        else:
            raise HTTPException(status_code=400, detail="Failed to save sales record.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Record New Stock (Inventory Management from your Figma mockup)
@router.post("/inventory", status_code=201)
def record_new_stock(stock_data: InventoryStockSchema):
    """
    API endpoint that receives incoming stock creation data from the client form modal.
    """
    try:
        success = add_stock_to_db(
            item_name=stock_data.item_name,
            size=stock_data.size,
            quantity=stock_data.quantity,
            unit=stock_data.unit
        )
        if success:
            return {"status": "success", "message": f"{stock_data.item_name} stock logged successfully!"}
        else:
            raise HTTPException(status_code=400, detail="Failed to log new inventory stock.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))