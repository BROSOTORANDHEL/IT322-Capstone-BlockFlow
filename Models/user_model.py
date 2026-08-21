from database import get_db_connection


class UserModel:
    @staticmethod
    def find_by_email(email: str):
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT id, email, password, role FROM users WHERE email = ? COLLATE NOCASE",
                (email,),
            ).fetchone()
            return dict(row) if row else None