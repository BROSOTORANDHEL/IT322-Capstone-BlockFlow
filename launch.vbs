Set WshShell = CreateObject("WScript.Shell")

' 1. Boot up the FastAPI server completely hidden
WshShell.Run "python -m uvicorn App:app --reload", 0, False

' 2. Wait 3 seconds for the backend server to spin up 
WScript.Sleep 3000

' 3. Launch your PyQt6 Login window
WshShell.Run "python login_view.py", 1, True

' 4. Clean up background server tasks when the window is closed
WshShell.Run "taskkill /f /im python.exe", 0, True