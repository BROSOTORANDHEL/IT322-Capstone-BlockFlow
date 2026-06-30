from database import get_db_connection
from pydantic import BaseModel

class UserModel:
    @staticmethod
    def find_by_email(email: str):
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            # Changed placeholder from %s to ? for SQLite compatibility
            sql = "SELECT id, email, password, role FROM users WHERE email = ?"
            cursor.execute(sql, (email,))
            row = cursor.fetchone()
            
            # Formats the row into a standard Python dict if found
            if row:
                return dict(row)
            return None
        finally:
            connection.close()
    

class ExpenseSchema(BaseModel):
    category: str
    description: str
    amount: float
    date_recorded: str