"""Small API client helpers for manual testing and integrations."""

from __future__ import annotations

import os
from typing import Any

import requests


BASE_URL = os.environ.get("BLOCKFLOW_API_URL", "http://127.0.0.1:8000/api").rstrip("/")


def _post(path: str, payload: dict[str, Any]) -> requests.Response:
    return requests.post(f"{BASE_URL}/{path.lstrip('/')}", json=payload, timeout=10)


def send_register_data(email: str, password: str, role: str = "staff"):
    return _post("register", {"email": email, "password": password, "role": role})


def send_login_data(email: str, password: str):
    return _post("login", {"email": email, "password": password})


def send_expense_data(
    description: str,
    amount: float,
    category: str,
    date_recorded: str,
):
    return _post(
        "expenses",
        {
            "expense_name": description,
            "amount": float(amount),
            "category": category,
            "date_added": date_recorded,
        },
    )