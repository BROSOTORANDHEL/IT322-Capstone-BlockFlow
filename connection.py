import requests

BASE_URL = "http://127.0.0.1:8000"

def send_register_data(email, password):
    """
    Registers a new user account in the database.
    """
    url = f"{BASE_URL}/api/register"
    
    payload = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(url, json=payload)
        return response
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Ensure Uvicorn is running.")
        return None

def send_login_data(email, password):
    """
    Sends user credentials (email) to the FastAPI backend.
    """
    url = f"{BASE_URL}/api/login"
    
    payload = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(url, json=payload)
        return response
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Ensure Uvicorn is running.")
        return None

def send_expense_data(title, amount, category, description, date_recorded):
    """
    Sends fully structured expense entries containing all required schema fields.
    """
    url = f"{BASE_URL}/api/expenses" 
    
    payload = {
        "title": title,
        "amount": float(amount),
        "category": category,
        "description": description,
        "date_recorded": date_recorded
    }
    
    try:
        response = requests.post(url, json=payload)
        return response
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Ensure Uvicorn is running.")
        return None

if __name__ == "__main__":
    print("--- Running Connection Test BlockFlow Backend ---")
    
    test_email = "absolutely_fresh_200@example.com"
    test_password = "password123"

    print("\nAttempting to Register New Account...")
    register_result = send_register_data(email=test_email, password=test_password)
    if register_result is not None:
        print(f"Register Status Code: {register_result.status_code}")
        print(f"Register Response: {register_result.text}")

    print("\nSending Test Login...")
    login_result = send_login_data(email=test_email, password=test_password)
    if login_result is not None:
        print(f"Login Status Code: {login_result.status_code}")
        if login_result.status_code == 200:
            print(f"Login Body Response: {login_result.json()}")
        else:
            print(f"Login Error Details: {login_result.text}")

    print("\nSending Test Expense Entry...")
    expense_result = send_expense_data(
        title="Internet Subscription", 
        amount=1499.00,
        category="Utilities",
        description="Monthly broadband payment",
        date_recorded="2026-06-30"
    )
    if expense_result is not None:
        print(f"Expense Status Code: {expense_result.status_code}")
        if expense_result.status_code in [200, 201]:
            print(f"Expense Body Response: {expense_result.json()}")
        else:
            print(f"Expense Error Details: {expense_result.text}")