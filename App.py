import sys
import threading
import uvicorn
from fastapi import FastAPI
from Routers import user_router
from PyQt6.QtWidgets import QApplication
from login_view import BlockFlowLogin

# 1. Multi-processing flag required for Windows binaries
from multiprocessing import freeze_support

app = FastAPI(title="BlockFlow API")
app.include_router(user_router.router, prefix="/api")

def run_backend():
    """Runs the FastAPI server reliably inside an EXE environment."""
    config = uvicorn.Config(
        app, 
        host="127.0.0.1", 
        port=8000, 
        log_level="warning",
        workers=1
    )
    server = uvicorn.Server(config)
    server.run()

def run_frontend():
    """Launches the PyQt6 Desktop Window on the main thread."""
    qt_app = QApplication(sys.argv)
    main_window = BlockFlowLogin()
    main_window.show()
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    # 2. Authorization hook that stops Windows from blocking the local network socket
    freeze_support()

    # Start the local FastAPI server loop in a background thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Launch the desktop software interface immediately
    run_frontend()
