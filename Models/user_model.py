from database import get_db_connection
from pydantic import BaseModel

class UserModel:
    @staticmethod
    def find_by_email(email: str):
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            sql = "SELECT id, email, password, role FROM users WHERE email = ?"
            cursor.execute(sql, (email,))
            row = cursor.fetchone()
            
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