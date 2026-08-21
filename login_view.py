import sys
import os
import requests
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor, QLinearGradient
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QMessageBox,
    QGraphicsOpacityEffect
)


class BlockFlowLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlockFlow — Business Management System")

        self.backend_url = os.environ.get(
            "BLOCKFLOW_API_URL", "http://127.0.0.1:8000/api"
        ).rstrip("/")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(script_dir, "image_b08741.png")
        if not os.path.exists(self.image_path):
            self.image_path = os.path.join(script_dir, "image_b08741.jpg")

        self.init_ui()
        self.setWindowOpacity(0.0)
        self.showFullScreen()
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(500)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Outer card wrapper ──────────────────────────────────────────────
        card = QFrame()
        card.setFixedSize(420, 600)
        card.setObjectName("LoginCard")
        card.setStyleSheet("""
            QFrame#LoginCard {
                background-color: rgba(10, 15, 30, 210);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 25);
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── Accent top bar (gradient) ────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setFixedHeight(4)
        top_bar.setObjectName("TopBar")
        top_bar.setStyleSheet("""
            QFrame#TopBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:0.5 #8B5CF6, stop:1 #10B981);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """)
        card_layout.addWidget(top_bar)

        # ── Inner form padding ───────────────────────────────────────────────
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(42, 36, 42, 36)
        inner_layout.setSpacing(0)

        # Brand logo badge
        logo_row = QHBoxLayout()
        logo_badge = QLabel("BF")
        logo_badge.setFixedSize(52, 52)
        logo_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_badge.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        logo_badge.setStyleSheet("""
            color: #FFFFFF;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #3B82F6, stop:1 #8B5CF6);
            border-radius: 14px;
        """)
        logo_row.addStretch()
        logo_row.addWidget(logo_badge)
        logo_row.addStretch()
        inner_layout.addLayout(logo_row)
        inner_layout.addSpacing(18)

        # Brand title
        title_label = QLabel("BlockFlow")
        title_label.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #F8FAFC;")
        inner_layout.addWidget(title_label)

        sub_label = QLabel("Magalin Hollow Blocks Trading")
        sub_label.setFont(QFont("Segoe UI", 10))
        sub_label.setStyleSheet("color: #64748B; letter-spacing: 1px;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(sub_label)
        inner_layout.addSpacing(32)

        # ── Divider ──────────────────────────────────────────────────────────
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: rgba(255,255,255,15);")
        inner_layout.addWidget(div)
        inner_layout.addSpacing(28)

        # ── Role selector ────────────────────────────────────────────────────
        role_label = QLabel("LOGIN ROLE")
        role_label.setStyleSheet("color: #475569; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        inner_layout.addWidget(role_label)
        inner_layout.addSpacing(6)

        self.role_box = QComboBox()
        self.role_box.addItems(["Admin / Owner", "Staff Member"])
        self.role_box.setStyleSheet("""
            QComboBox {
                background-color: rgba(30, 41, 59, 180);
                color: #F8FAFC;
                border: 1px solid rgba(255,255,255,18);
                border-radius: 10px;
                padding: 11px 14px;
                font-size: 13px;
            }
            QComboBox:focus { border: 1px solid #3B82F6; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #F8FAFC;
                selection-background-color: #334155;
                border: 1px solid #334155;
            }
        """)
        inner_layout.addWidget(self.role_box)
        inner_layout.addSpacing(16)

        # ── Email field ──────────────────────────────────────────────────────
        email_label = QLabel("EMAIL ADDRESS")
        email_label.setStyleSheet("color: #475569; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        inner_layout.addWidget(email_label)
        inner_layout.addSpacing(6)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("your@email.com")
        self._style_input(self.user_input)
        inner_layout.addWidget(self.user_input)
        inner_layout.addSpacing(16)

        # ── Password field ───────────────────────────────────────────────────
        pass_label = QLabel("PASSWORD")
        pass_label.setStyleSheet("color: #475569; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        inner_layout.addWidget(pass_label)
        inner_layout.addSpacing(6)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Enter password")
        self._style_input(self.pass_input)
        inner_layout.addWidget(self.pass_input)
        inner_layout.addSpacing(28)

        # ── Sign in button ───────────────────────────────────────────────────
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("SignInBtn")
        self.login_btn.setFixedHeight(48)
        self.login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.login_btn.setStyleSheet("""
            QPushButton#SignInBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB, stop:1 #4F46E5);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton#SignInBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1D4ED8, stop:1 #4338CA);
            }
            QPushButton#SignInBtn:pressed {
                background: #1E40AF;
            }
        """)
        inner_layout.addWidget(self.login_btn)
        inner_layout.addSpacing(14)

        # ── Register link ────────────────────────────────────────────────────
        self.register_btn = QPushButton("Create an account / Register Staff")
        self.register_btn.setObjectName("RegisterLink")
        self.register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_btn.setStyleSheet("""
            QPushButton#RegisterLink {
                background-color: transparent;
                color: #3B82F6;
                border: none;
                font-size: 13px;
                text-decoration: underline;
            }
            QPushButton#RegisterLink:hover { color: #60A5FA; }
        """)
        inner_layout.addWidget(self.register_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        inner_layout.addSpacing(10)

        # ── Exit button ──────────────────────────────────────────────────────
        self.exit_btn = QPushButton("Exit Program")
        self.exit_btn.setObjectName("ExitBtn")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setFixedHeight(40)
        self.exit_btn.setStyleSheet("""
            QPushButton#ExitBtn {
                background-color: transparent;
                color: #64748B;
                border: 1px solid rgba(255,255,255,15);
                border-radius: 10px;
                font-size: 13px;
            }
            QPushButton#ExitBtn:hover {
                background-color: rgba(239, 68, 68, 0.15);
                color: #F87171;
                border-color: rgba(239, 68, 68, 0.3);
            }
        """)
        inner_layout.addWidget(self.exit_btn)
        inner_layout.addStretch()

        card_layout.addWidget(inner)
        main_layout.addWidget(card)
        self.setLayout(main_layout)

        # Connect signals
        self.login_btn.clicked.connect(self.handle_api_login)
        self.register_btn.clicked.connect(self.handle_api_registration)
        self.exit_btn.clicked.connect(self.close)
        self.pass_input.returnPressed.connect(self.handle_api_login)

    def _style_input(self, field: QLineEdit):
        field.setFixedHeight(46)
        field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 41, 59, 180);
                color: #F8FAFC;
                border: 1px solid rgba(255,255,255,18);
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #3B82F6; background-color: rgba(30, 41, 59, 220); }
            QLineEdit::placeholder { color: #475569; }
        """)

    # ── Login handler ────────────────────────────────────────────────────────
    def handle_api_login(self):
        email = self.user_input.text().strip()
        password = self.pass_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Input Error", "Please fill in all email and password fields.")
            return

        try:
            payload = {
                "email": email,
                "password": password,
                "role": self.role_box.currentText(),
            }
            response = requests.post(
                f"{self.backend_url}/login", json=payload, timeout=10
            )

            if response.status_code in (200, 201):
                data = response.json()
                user_role = data.get('role', 'client')

                if "owner" in user_role.lower() or "admin" in user_role.lower():
                    try:
                        from dashboard_view import BlockFlowDashboard
                        self.dashboard_window = BlockFlowDashboard(role=user_role)
                        self.dashboard_window.showFullScreen()
                        self.close()
                    except ImportError:
                        QMessageBox.critical(self, "Import Error", "Could not find 'dashboard_view.py'.")
                else:
                    try:
                        from inventory_view import BlockFlowInventory
                        self.inventory_window = BlockFlowInventory(role=user_role)
                        self.inventory_window.showFullScreen()
                        self.close()
                    except ImportError:
                        QMessageBox.critical(self, "Import Error", "Could not find 'inventory_view.py'.")
            else:
                detail = response.json().get("detail", "Invalid credentials")
                QMessageBox.critical(self, "Login Failed", f"Authentication Rejected:\n{detail}")

        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Server Error",
                "Could not connect to the Backend server!\nMake sure App.py is running.")

    # ── Register handler ─────────────────────────────────────────────────────
    def handle_api_registration(self):
        email = self.user_input.text().strip()
        password = self.pass_input.text()
        if not email or not password:
            QMessageBox.warning(self, "Registration Error",
                "Please provide an email and password to create an account.")
            return

        try:
            payload = {
                "email": email,
                "password": password,
                "role": self.role_box.currentText(),
            }
            response = requests.post(
                f"{self.backend_url}/register", json=payload, timeout=10
            )

            if response.status_code in (200, 201):
                data = response.json()
                QMessageBox.information(self, "Registration Success", data.get("message"))
                self.user_input.clear()
                self.pass_input.clear()
            else:
                detail = response.json().get("detail", "Failed to register user")
                QMessageBox.warning(self, "Registration Failed", f"Backend rejected command:\n{detail}")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Server Error",
                "Could not connect to the Backend server!\nMake sure App.py is running.")

    # ── Background painting ──────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#080D1A"))
        pixmap = QPixmap(self.image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.fillRect(self.rect(), QColor(5, 10, 25, 195))
        painter.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = BlockFlowLogin()
    window.show()
    sys.exit(app.exec())
