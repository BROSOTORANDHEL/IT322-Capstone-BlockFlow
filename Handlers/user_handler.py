from fastapi import HTTPException, status
from pydantic import BaseModel
import hashlib
from Models.user_model import UserModel

# This tells Swagger UI exactly what fields to show you
class LoginSchema(BaseModel):
    email: str
    password: str

def login_handler(login_data: LoginSchema):
    email = login_data.email
    password = login_data.password

    # Search for user match in the database
    user = UserModel.find_by_email(email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Hash the input string parameter via built-in SHA-256 matching
    hashed_input_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # Validation block against MySQL data record
    if hashed_input_password != user['password']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    return {
        "message": "Login successful",
        "user": {
            "id": user['id'],
            "email": user['email'],
            "role": user['role'] # Returns 'owner' or 'client'
        }
    }