import sys
import os
import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QMessageBox
)

class BlockFlowLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlockFlow - Business Management System")
        
        # Base URL for your FastAPI Backend application (App.py)
        self.backend_url = "http://127.0.0.1:8000/api"
        
        # Resolve assets path seamlessly
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(script_dir, "image_b08741.png")
        if not os.path.exists(self.image_path):
            self.image_path = os.path.join(script_dir, "image_b08741.jpg")

        self.init_ui()
        self.showFullScreen()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Translucent glass login form card wrapper
        card = QFrame()
        card.setFixedSize(400, 580)
        card.setObjectName("LoginCard")
        card.setStyleSheet("""
            QFrame#LoginCard {
                background-color: rgba(30, 41, 59, 230); 
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 15);
            }
            QLabel { color: #F8FAFC; }
            QComboBox {
                background-color: #1E293B; color: #F8FAFC;
                border: 1px solid #475569; border-radius: 6px;
                padding: 8px; font-size: 13px;
            }
            QLineEdit {
                background-color: #1E293B; color: #F8FAFC;
                border: 1px solid #475569; border-radius: 6px;
                padding: 10px; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #3B82F6; }
            QPushButton#SignInBtn {
                background-color: #2563EB; color: white;
                border-radius: 6px; font-weight: bold; font-size: 14px; padding: 12px;
            }
            QPushButton#SignInBtn:hover { background-color: #1D4ED8; }
            QPushButton#RegisterLink {
                background-color: transparent; color: #3B82F6; border: none; font-size: 13px;
            }
            QPushButton#RegisterLink:hover { color: #60A5FA; }
            QPushButton#ExitBtn {
                background-color: transparent; color: #94A3B8;
                border: 1px solid #475569; border-radius: 6px; font-size: 13px; padding: 8px;
            }
            QPushButton#ExitBtn:hover { background-color: #EF4444; color: white; border: 1px solid #EF4444; }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(12)

        title_label = QLabel("BlockFlow")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)

        sub_label = QLabel("Business Management System")
        sub_label.setFont(QFont("Arial", 10))
        sub_label.setStyleSheet("color: #94A3B8;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(sub_label)
        card_layout.addSpacing(10)
        
        role_label = QLabel("Login Role")
        role_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.role_box = QComboBox()
        self.role_box.addItems(["Admin / Owner", "Staff Member"])
        card_layout.addWidget(role_label)
        card_layout.addWidget(self.role_box)

        user_label = QLabel("Email Address")
        user_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Enter your email address")
        card_layout.addWidget(user_label)
        card_layout.addWidget(self.user_input)

        pass_label = QLabel("Password")
        pass_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Enter password")
        card_layout.addWidget(pass_label)
        card_layout.addWidget(self.pass_input)

        card_layout.addSpacing(10)

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("SignInBtn")
        card_layout.addWidget(self.login_btn)

        self.register_btn = QPushButton("Create an account / Register Staff")
        self.register_btn.setObjectName("RegisterLink")
        self.register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(self.register_btn)
        
        card_layout.addSpacing(5)

        self.exit_btn = QPushButton("Exit Program")
        self.exit_btn.setObjectName("ExitBtn")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(self.exit_btn)

        main_layout.addWidget(card)
        self.setLayout(main_layout)

        # Connect button click triggers
        self.login_btn.clicked.connect(self.handle_api_login)
        self.register_btn.clicked.connect(self.handle_api_registration)
        self.exit_btn.clicked.connect(self.close)

    # 🔑 ACTION: Login through FastAPI Server
    def handle_api_login(self):
        email = self.user_input.text().strip()
        password = self.pass_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Input Error", "Please fill in all email and password fields.")
            return

        try:
            payload = {"email": email, "password": password}
            response = requests.post(f"{self.backend_url}/login", json=payload)

            if response.status_code == 200:
                data = response.json()
                user_role = data.get('role', 'client')
                
                # 🚀 REDIRECT ADMIN/OWNER TO THE DASHBOARD
                if "owner" in user_role.lower() or "admin" in user_role.lower():
                    try:
                        from dashboard_view import BlockFlowDashboard
                        self.dashboard_window = BlockFlowDashboard()
                        self.dashboard_window.showFullScreen()
                        self.close()  # Safely closes login window
                    except ImportError:
                        QMessageBox.critical(self, "Import Error", "Could not find 'dashboard_view.py'. Ensure the file template exists!")
                
                # 📦 REDIRECT STAFF MEMBERS STRAIGHT TO INVENTORY VIEW
                else:
                    try:
                        from inventory_view import BlockFlowInventory
                        self.inventory_window = BlockFlowInventory()
                        self.inventory_window.showFullScreen()
                        self.close()  # Safely closes login window
                    except ImportError:
                        QMessageBox.critical(self, "Import Error", "Could not find 'inventory_view.py'. Verify the filename capitalization!")
            else:
                detail = response.json().get("detail", "Invalid credentials")
                QMessageBox.critical(self, "Login Failed", f"Authentication Rejected:\n{detail}")
                
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Server Error", "Could not connect to the Backend server!\nMake sure App.py is running.")

    # 📝 ACTION: Registration through FastAPI Server
    def handle_api_registration(self):
        email = self.user_input.text().strip()
        password = self.pass_input.text()
        selected_role = self.role_box.currentText()

        db_role = "owner" if "Admin" in selected_role else "client"

        if not email or not password:
            QMessageBox.warning(self, "Registration Error", "Please provide an email and password to create an account.")
            return

        try:
            payload = {"email": email, "password": password, "role": db_role}
            response = requests.post(f"{self.backend_url}/register", json=payload)

            if response.status_code == 200:
                data = response.json()
                QMessageBox.information(self, "Registration Success", data.get("message"))
                self.user_input.clear()
                self.pass_input.clear()
            else:
                detail = response.json().get("detail", "Failed to register user")
                QMessageBox.warning(self, "Registration Failed", f"Backend rejected command:\n{detail}")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Server Error", "Could not connect to the Backend server!\nMake sure App.py is running.")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0F172A"))
        pixmap = QPixmap(self.image_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.fillRect(self.rect(), QColor(15, 23, 42, 160)) 
        painter.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BlockFlowLogin()
    window.show()
    sys.exit(app.exec())