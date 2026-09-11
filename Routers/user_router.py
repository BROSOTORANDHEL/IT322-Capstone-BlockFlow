from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from database import (
    get_all_expenses,
    get_all_inventory,
    get_all_sales,
    get_transaction_history,
    record_expense,
    record_new_stock,
    record_sale,
    register_user,
    verify_user_login,
)


router = APIRouter()


def _request_recorded_by(payload_value: str, role_header: str | None) -> str:
    """Resolve the recorder from the active desktop role.

    The desktop sends both the role-derived payload and an explicit header.
    The header prevents a stale/default Pydantic value ("staff") from
    overwriting an Admin/Owner record.
    """
    raw = role_header if role_header is not None else payload_value
    clean = (raw or "staff").strip().lower()
    return "owner" if clean in {"owner", "admin", "admin / owner", "admin/owner"} else "staff"


class ExpenseRequest(BaseModel):
    expense_name: str = Field(min_length=1)
    amount: float = Field(gt=0)
    category: str = Field(min_length=1)
    date_added: str = Field(min_length=8)
    recorded_by: str = "staff"


class InventoryRequest(BaseModel):
    quantity: int = Field(gt=0)
    price: float = Field(ge=0)
    date_added: str = Field(min_length=8)
    size: str = "None"
    unit: str = "pcs"
    recorded_by: str = "staff"


class SalesRequest(BaseModel):
    customer_name: str = Field(min_length=1)
    customer_number: str = Field(min_length=1)
    shop_name: str = Field(min_length=1)
    block_size: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    recorded_by: str = "staff"
    sale_date: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)
    role: str = "staff"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    role: str = "staff"


@router.get("/health")
def health() -> dict[str, str]:
    # Version marker: useful for confirming that the backend process was
    # restarted after installing the updated project.
    return {"status": "ok", "recorded_by_fix": "v4-2026-09-11"}


@router.post("/login")
def login(data: LoginRequest) -> dict[str, str]:
    user = verify_user_login(data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    selected_role = data.role.strip().lower()
    selected_role = (
        "owner"
        if selected_role in {"owner", "admin", "admin / owner"}
        else "staff"
    )
    if user["role"] != selected_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The selected login role does not match this account",
        )

    return {
        "status": "success",
        "message": "Logged in successfully",
        "role": user["role"],
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest) -> dict[str, str]:
    try:
        # This deployment uses the role selected by the trusted users.
        created = register_user(data.email, data.password, data.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not created:
        raise HTTPException(status_code=409, detail="This email is already registered")
    return {"status": "success", "message": "Account created successfully"}


@router.get("/expenses")
def get_expenses() -> list[dict]:
    return get_all_expenses()


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
def add_expense(data: ExpenseRequest, x_blockflow_role: str | None = Header(default=None)) -> dict[str, str | int]:
    try:
        expense_id = record_expense(
            expense_name=data.expense_name,
            amount=data.amount,
            category=data.category,
            date_added=data.date_added,
            recorded_by=_request_recorded_by(data.recorded_by, x_blockflow_role),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "message": "Expense transaction saved", "id": expense_id}


@router.get("/inventory")
def get_inventory() -> list[dict]:
    return get_all_inventory()


@router.post("/inventory", status_code=status.HTTP_201_CREATED)
def add_inventory(data: InventoryRequest, x_blockflow_role: str | None = Header(default=None)) -> dict[str, str | int]:
    try:
        inventory_id = record_new_stock(
            quantity=data.quantity,
            price=data.price,
            date_added=data.date_added,
            size=data.size,
            unit=data.unit,
            recorded_by=_request_recorded_by(data.recorded_by, x_blockflow_role),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "success",
        "message": "Inventory restock tracked",
        "id": inventory_id,
    }


@router.get("/sales")
def get_sales() -> list[dict]:
    return get_all_sales()


@router.post("/sales", status_code=status.HTTP_201_CREATED)
def add_sale(data: SalesRequest, x_blockflow_role: str | None = Header(default=None)) -> dict[str, str | int]:
    try:
        sale_id = record_sale(
            customer_name=data.customer_name,
            customer_number=data.customer_number,
            shop_name=data.shop_name,
            block_size=data.block_size,
            quantity=data.quantity,
            sale_date=data.sale_date,
            recorded_by=_request_recorded_by(data.recorded_by, x_blockflow_role),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "message": "Sale logged successfully", "id": sale_id}


@router.get("/history")
def view_transaction_history() -> list[dict]:
    return get_transaction_history()