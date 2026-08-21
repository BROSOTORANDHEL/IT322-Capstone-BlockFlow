"""SQLite persistence for BlockFlow.

The original project had several competing database initializers and mixed
plain-text, SHA-256, and role-specific authentication behavior.  This module
is the single source of truth for the fixed application.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any


DB_PATH = Path(
    os.environ.get(
        "BLOCKFLOW_DB_PATH",
        str(Path(__file__).resolve().with_name("blockflow.db")),
    )
)
PASSWORD_ITERATIONS = 210_000
HOLLOWBLOCKS_ITEM_NAME = "Hollowblocks"
# One application-wide alert level for the combined current stock.  This is
# intentionally not stored on individual stock entries.
LOW_STOCK_ALERT_THRESHOLD = 100


def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _today(value: str | None = None) -> str:
    return value or date.today().isoformat()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalise_role(role: str | None) -> str:
    value = (role or "staff").strip().lower()
    return "owner" if value in {"owner", "admin", "admin / owner"} else "staff"


def _normalise_size(size: str | None) -> str:
    value = (size or "None").strip()
    upper = value.upper()
    if "XL" in upper:
        return "XL"
    if upper.startswith("L") or "L (LARGE)" in upper:
        return "L"
    return "None"


def price_for_size(size: str | None) -> float:
    return 8.0 if _normalise_size(size) == "XL" else 7.0


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    columns = {
        row["name"] for row in conn.execute(f'PRAGMA table_info("{table}")')
    }
    if column not in columns:
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')


def ensure_schema_integrity() -> None:
    """Create the current schema and make old local databases readable.

    Existing tables are preserved where possible.  New installations start
    with the same schema, so API behavior is identical on every machine.
    """

    with get_db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'staff',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                size TEXT NOT NULL DEFAULT 'None',
                quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                unit TEXT NOT NULL DEFAULT 'pcs',
                price REAL NOT NULL DEFAULT 0,
                low_stock_threshold INTEGER NOT NULL DEFAULT 100,
                date_recorded TEXT,
                date_added TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                shop_name TEXT NOT NULL,
                block_size TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price REAL NOT NULL DEFAULT 0,
                total_amount REAL NOT NULL DEFAULT 0,
                sale_date TEXT NOT NULL,
                date_logged TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                date_recorded TEXT NOT NULL,
                date_logged TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('sale', 'expense', 'inventory')),
                date_record TEXT NOT NULL,
                source_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Migrate columns used by older versions without dropping user data.
        for column, definition in (
            ("role", "TEXT NOT NULL DEFAULT 'staff'"),
            ("created_at", "TEXT"),
        ):
            _ensure_column(conn, "users", column, definition)
        for column, definition in (
            ("price", "REAL NOT NULL DEFAULT 0"),
            ("low_stock_threshold", "INTEGER NOT NULL DEFAULT 100"),
            ("date_added", "TEXT"),
            ("date_recorded", "TEXT"),
            ("created_at", "TEXT"),
        ):
            _ensure_column(conn, "inventory", column, definition)
        for column, definition in (
            ("unit_price", "REAL NOT NULL DEFAULT 0"),
            ("total_amount", "REAL NOT NULL DEFAULT 0"),
            ("date_logged", "TEXT"),
        ):
            _ensure_column(conn, "sales", column, definition)

        # Older databases may have an expenses table with different names.
        # Copy legacy values into the current fields when those fields exist.
        expense_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(expenses)")
        }
        if "description" not in expense_columns:
            _ensure_column(conn, "expenses", "description", "TEXT")
        if "category" not in expense_columns:
            _ensure_column(conn, "expenses", "category", "TEXT")
        if "amount" not in expense_columns:
            _ensure_column(conn, "expenses", "amount", "REAL")
        if "date_recorded" not in expense_columns:
            _ensure_column(conn, "expenses", "date_recorded", "TEXT")
        if "expense_name" in expense_columns:
            conn.execute(
                "UPDATE expenses SET description = COALESCE(NULLIF(description, ''), expense_name)"
            )
        if "date_added" in expense_columns:
            conn.execute(
                "UPDATE expenses SET date_recorded = COALESCE(NULLIF(date_recorded, ''), date_added)"
            )
        conn.execute(
            "UPDATE expenses SET category = COALESCE(NULLIF(category, ''), 'Others')"
        )
        conn.execute(
            "UPDATE expenses SET date_recorded = COALESCE(NULLIF(date_recorded, ''), ?)",
            (_today(),),
        )

        # Normalize old records so the API always returns the same shape.
        conn.execute(
            "UPDATE inventory SET size = 'None' WHERE size IS NULL OR TRIM(size) = ''"
        )
        conn.execute(
            "UPDATE inventory SET unit = 'pcs' WHERE unit IS NULL OR TRIM(unit) = ''"
        )
        # BlockFlow tracks one finished product.  Normalize older records so
        # legacy databases cannot reintroduce a different item name.
        conn.execute(
            "UPDATE inventory SET item_name = ? "
            "WHERE item_name IS NULL OR TRIM(item_name) = '' OR item_name <> ?",
            (HOLLOWBLOCKS_ITEM_NAME, HOLLOWBLOCKS_ITEM_NAME),
        )
        conn.execute(
            "UPDATE inventory SET date_added = COALESCE(date_added, date_recorded, ?)",
            (_today(),),
        )
        conn.execute(
            "UPDATE inventory SET date_recorded = COALESCE(date_recorded, date_added, ?)",
            (_today(),),
        )
        conn.execute(
            """
            UPDATE sales
            SET unit_price = CASE
                WHEN unit_price IS NULL OR unit_price = 0 THEN
                    CASE WHEN UPPER(block_size) LIKE '%XL%' THEN 8.0 ELSE 7.0 END
                ELSE unit_price
            END,
            total_amount = CASE
                WHEN total_amount IS NULL OR total_amount = 0
                    THEN quantity * CASE WHEN UPPER(block_size) LIKE '%XL%' THEN 8.0 ELSE 7.0 END
                ELSE total_amount
            END,
            sale_date = COALESCE(NULLIF(sale_date, ''), ?)
            """,
            (_today(),),
        )

        # Backfill the canonical transaction log once for legacy operational
        # records. Existing dashboard duplicates are intentionally ignored.
        transaction_count = conn.execute(
            "SELECT COUNT(*) AS count FROM transactions"
        ).fetchone()["count"]
        if transaction_count == 0:
            conn.execute(
                """
                INSERT INTO transactions (title, amount, type, date_record, source_id)
                SELECT customer_name || ' — ' || quantity || ' pcs (' || block_size || ')',
                       total_amount, 'sale', sale_date, id
                FROM sales
                ORDER BY id
                """
            )
            conn.execute(
                """
                INSERT INTO transactions (title, amount, type, date_record, source_id)
                SELECT description, -amount, 'expense', date_recorded, id
                FROM expenses
                ORDER BY id
                """
            )
            conn.execute(
                """
                INSERT INTO transactions (title, amount, type, date_record, source_id)
                SELECT 'Stocked: ' || item_name, price * quantity, 'inventory',
                       COALESCE(date_added, date_recorded, ?), id
                FROM inventory
                ORDER BY id
                """,
                (_today(),),
            )


def _hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> tuple[bool, bool]:
    """Return (is_valid, should_upgrade)."""
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt_hex, digest_hex = stored.split("$", 3)
            expected = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            ).hex()
            return hmac.compare_digest(expected, digest_hex), False
        except (ValueError, TypeError):
            return False, False

    # Gracefully upgrade old SHA-256 or plain-text demo accounts after the
    # first successful login. New accounts never use either legacy format.
    sha256_match = hmac.compare_digest(
        hashlib.sha256(password.encode("utf-8")).hexdigest(), stored
    )
    if sha256_match or hmac.compare_digest(password, stored):
        return True, True
    return False, False


def register_user(email: str, password: str, role: str = "staff") -> bool:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Enter a valid email address")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    ensure_schema_integrity()
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (email, password, role, created_at) VALUES (?, ?, ?, ?)",
                (email, _hash_password(password), _normalise_role(role), _now()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user_login(email: str, password: str) -> dict[str, str] | None:
    ensure_schema_integrity()
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password, role FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip(),),
        ).fetchone()
        if not row:
            return None
        valid, should_upgrade = _verify_password(password, row["password"])
        if not valid:
            return None
        if should_upgrade:
            conn.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (_hash_password(password), row["id"]),
            )
        return {"id": str(row["id"]), "email": row["email"], "role": _normalise_role(row["role"])}


def record_new_stock(
    quantity: int,
    price: float,
    date_added: str | None,
    size: str = "None",
    unit: str = "pcs",
) -> int:
    ensure_schema_integrity()
    quantity = int(quantity)
    price = float(price)
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    if price < 0:
        raise ValueError("Price cannot be negative")
    recorded_date = _today(date_added)
    clean_size = _normalise_size(size)
    clean_unit = unit.strip() or "pcs"
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO inventory
                (item_name, quantity, size, unit, price, low_stock_threshold,
                 date_added, date_recorded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                HOLLOWBLOCKS_ITEM_NAME,
                quantity,
                clean_size,
                clean_unit,
                price,
                LOW_STOCK_ALERT_THRESHOLD,
                recorded_date,
                recorded_date,
            ),
        )
        inventory_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO transactions (title, amount, type, date_record, source_id)
            VALUES (?, ?, 'inventory', ?, ?)
            """,
            (
                f"Stocked: {HOLLOWBLOCKS_ITEM_NAME}",
                price * quantity,
                recorded_date,
                inventory_id,
            ),
        )
    return int(inventory_id)


def record_sale(
    customer_name: str,
    shop_name: str,
    block_size: str,
    quantity: int,
    sale_date: str | None,
) -> int:
    ensure_schema_integrity()
    customer_name = customer_name.strip()
    shop_name = shop_name.strip()
    quantity = int(quantity)
    if not customer_name or not shop_name:
        raise ValueError("Customer and shop names are required")
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    clean_size = _normalise_size(block_size)
    unit_price = price_for_size(clean_size)
    recorded_date = _today(sale_date)
    with get_db_connection() as conn:
        # Consume finished-goods stock from oldest entries first. "None" is
        # accepted as legacy/general stock, but other products are not.
        rows = conn.execute(
            """
            SELECT id, quantity
            FROM inventory
            WHERE unit = 'pcs' AND quantity > 0
              AND (size = ? OR size = 'None')
            ORDER BY id
            """,
            (clean_size,),
        ).fetchall()
        available = sum(int(row["quantity"]) for row in rows)
        if available < quantity:
            raise ValueError(
                f"Not enough {clean_size} stock. Available: {available:,} pcs."
            )

        remaining = quantity
        for row in rows:
            if remaining <= 0:
                break
            consumed = min(remaining, int(row["quantity"]))
            conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE id = ?",
                (consumed, row["id"]),
            )
            remaining -= consumed

        total_amount = quantity * unit_price
        cursor = conn.execute(
            """
            INSERT INTO sales
                (customer_name, shop_name, block_size, quantity, unit_price,
                 total_amount, sale_date, date_logged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_name,
                shop_name,
                clean_size,
                quantity,
                unit_price,
                total_amount,
                recorded_date,
                _now(),
            ),
        )
        sale_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO transactions (title, amount, type, date_record, source_id)
            VALUES (?, ?, 'sale', ?, ?)
            """,
            (
                f"{clean_size} x{quantity} — {customer_name} ({shop_name})",
                total_amount,
                recorded_date,
                sale_id,
            ),
        )
    return int(sale_id)


def record_expense(
    expense_name: str, amount: float, category: str, date_added: str | None
) -> int:
    ensure_schema_integrity()
    description = expense_name.strip()
    amount = float(amount)
    category = category.strip() or "Others"
    if not description:
        raise ValueError("Expense description is required")
    if amount <= 0:
        raise ValueError("Expense amount must be greater than zero")
    recorded_date = _today(date_added)
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses (category, description, amount, date_recorded, date_logged)
            VALUES (?, ?, ?, ?, ?)
            """,
            (category, description, amount, recorded_date, _now()),
        )
        expense_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO transactions (title, amount, type, date_record, source_id)
            VALUES (?, ?, 'expense', ?, ?)
            """,
            (description, -amount, recorded_date, expense_id),
        )
    return int(expense_id)


def get_all_expenses() -> list[dict[str, Any]]:
    ensure_schema_integrity()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, category, description, amount, date_recorded
            FROM expenses ORDER BY date_recorded DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_inventory() -> list[dict[str, Any]]:
    ensure_schema_integrity()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, item_name, size, quantity, unit, price,
                   date_added, date_recorded
            FROM inventory ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_sales() -> list[dict[str, Any]]:
    ensure_schema_integrity()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, customer_name, shop_name, block_size, quantity,
                   unit_price, total_amount, sale_date
            FROM sales ORDER BY sale_date DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_transaction_history() -> list[dict[str, Any]]:
    ensure_schema_integrity()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, amount, type, date_record
            FROM transactions
            ORDER BY id DESC
            """
        ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "description": row["title"],
            "amount": row["amount"],
            "type": row["type"],
            "date": row["date_record"],
        }
        for row in rows
    ]


ensure_schema_integrity()