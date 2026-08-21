"""Compatibility helpers for code that imports the original handler module."""

from pydantic import BaseModel, Field

from database import register_user, verify_user_login


class LoginSchema(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


def login_handler(login_data: LoginSchema) -> dict:
    user = verify_user_login(login_data.email, login_data.password)
    if not user:
        raise ValueError("Invalid email or password")
    return {
        "message": "Login successful",
        "user": user,
    }


def register_handler(email: str, password: str, role: str = "staff") -> bool:
    return register_user(email, password, role)