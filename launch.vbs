Set WshShell = CreateObject("WScript.Shell")
projectDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = projectDir

' 0. Kill any stale server/app instances left over from a previous run so
'    the new one can bind to the port and actually uses the latest code.
WshShell.Run "taskkill /f /im python.exe", 0, True
WScript.Sleep 500

' 1. Boot up the FastAPI server completely hidden
WshShell.Run "cmd /c cd /d """ & projectDir & """ && python -m uvicorn App:app --reload", 0, False

' 2. Wait 3 seconds for the backend server to spin up 
WScript.Sleep 3000

' 3. Launch your PyQt6 Login window
WshShell.Run "cmd /c cd /d """ & projectDir & """ && python login_view.py", 1, True

' 4. Clean up background server tasks when the window is closed
WshShell.Run "taskkill /f /im python.exe", 0, True