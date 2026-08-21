"""Initialize BlockFlow's database and optionally create an owner account."""

from __future__ import annotations

import argparse
import getpass

from database import ensure_schema_integrity, register_user


def initialize(email: str | None = None, password: str | None = None) -> None:
    ensure_schema_integrity()
    if email and password:
        try:
            created = register_user(email, password, "owner")
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if not created:
            raise SystemExit("That email is already registered.")
        print(f"Owner account created for {email}.")
    else:
        print("Database schema is ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the BlockFlow database")
    parser.add_argument("--email", help="Owner email to create")
    parser.add_argument("--password", help="Owner password; omit to enter it securely")
    args = parser.parse_args()
    password = args.password
    if args.email and password is None:
        password = getpass.getpass("Owner password (8+ characters): ")
    initialize(args.email, password)