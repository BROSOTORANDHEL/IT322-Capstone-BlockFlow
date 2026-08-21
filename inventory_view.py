import sys
import os
import json
from PyQt6.QtCore import Qt, QDate, QUrl, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QLinearGradient, QBrush
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QComboBox, QLineEdit, QDateEdit, QMessageBox,
    QGraphicsOpacityEffect, QSizePolicy
)

BASE_API_URL = os.environ.get(
    "BLOCKFLOW_API_URL", "http://127.0.0.1:8000/api"
).rstrip("/")

# ── Shared modal stylesheet ────────────────────────────────────────────────────
MODAL_BASE_STYLE = """
    QDialog {
        background-color: #080D1A;
        border: 1px solid rgba(255,255,255,18);
        border-radius: 18px;
    }
    QLabel { color: #B8C5D6; font-size: 12px; font-weight: bold; letter-spacing: 0.5px; }
    QLineEdit, QComboBox, QDateEdit {
        background-color: rgba(30,41,59,200);
        color: #F1F5F9;
        border: 1px solid rgba(255,255,255,15);
        border-radius: 10px;
        padding: 11px 14px;
        font-size: 13px;
        min-height: 18px;
    }
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
        border: 1px solid #3B82F6;
        background-color: rgba(30,41,59,240);
    }
    QLineEdit::placeholder { color: #94A3B8; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox QAbstractItemView {
        background-color: #111827;
        color: #F1F5F9;
        selection-background-color: #1E293B;
        border: 1px solid rgba(255,255,255,12);
    }
    QPushButton {
        font-size: 14px; font-weight: bold;
        border-radius: 10px; padding: 12px;
    }
"""


def _make_top_bar(color_start="#3B82F6", color_end="#8B5CF6"):
    bar = QFrame()
    bar.setFixedHeight(3)
    bar.setStyleSheet(f"""
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 {color_start}, stop:1 {color_end});
        border-top-left-radius: 18px;
        border-top-right-radius: 18px;
    """)
    return bar


def _make_modal_header(title_text, close_callback):
    layout = QHBoxLayout()
    layout.setSpacing(0)
    title = QLabel(title_text)
    title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
    title.setStyleSheet("color: #F1F5F9; font-size: 17px; font-weight: bold; letter-spacing: 0;")
    btn = QPushButton("✕")
    btn.setFixedSize(32, 32)
    btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(255,255,255,8);
            color: #94A3B8; border: none;
            border-radius: 8px; font-size: 14px;
        }
        QPushButton:hover { background-color: rgba(239,68,68,0.2); color: #F87171; }
    """)
    btn.clicked.connect(close_callback)
    layout.addWidget(title)
    layout.addStretch()
    layout.addWidget(btn)
    return layout


def _field_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet("color: #AAB8CA; font-size: 10px; font-weight: bold; letter-spacing: 1.2px;")
    return lbl


# =============================================================================
# RECORD SALES MODAL
# =============================================================================
class RecordSalesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Sale")
        self.setFixedSize(460, 470)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(MODAL_BASE_STYLE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_make_top_bar("#10B981", "#3B82F6"))

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(26, 20, 26, 22)
        layout.setSpacing(10)

        layout.addLayout(_make_modal_header("Record Sale", self.reject))
        layout.addSpacing(3)

        layout.addWidget(_field_label("Customer Name"))
        self.input_cust = QLineEdit()
        self.input_cust.setPlaceholderText("e.g., Juan Dela Cruz")
        layout.addWidget(self.input_cust)

        layout.addWidget(_field_label("Construction Shop"))
        self.input_shop = QLineEdit()
        self.input_shop.setPlaceholderText("e.g., ABC Construction Supply")
        layout.addWidget(self.input_shop)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)
        col1 = QVBoxLayout()
        col1.setSpacing(6)
        col1.addWidget(_field_label("Hollowblock Size"))
        self.combo_size = QComboBox()
        self.combo_size.addItems(["L (Large) — ₱7/pc", "XL (Extra Large) — ₱8/pc"])
        col1.addWidget(self.combo_size)
        col2 = QVBoxLayout()
        col2.setSpacing(6)
        col2.addWidget(_field_label("Quantity (pcs)"))
        self.input_qty = QLineEdit()
        self.input_qty.setPlaceholderText("0")
        col2.addWidget(self.input_qty)
        row_layout.addLayout(col1, stretch=3)
        row_layout.addLayout(col2, stretch=2)
        layout.addLayout(row_layout)

        layout.addWidget(_field_label("Sale Date"))
        self.input_date = QDateEdit()
        self.input_date.setDate(QDate.currentDate())
        self.input_date.setCalendarPopup(True)
        self.input_date.setDisplayFormat("MM/dd/yyyy")
        layout.addWidget(self.input_date)

        layout.addSpacing(6)
        self.btn_submit = QPushButton("Record Sale")
        self.btn_submit.setFixedHeight(42)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #059669, stop:1 #10B981);
                color: white; border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #047857, stop:1 #059669);
            }
        """)
        self.btn_submit.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.btn_submit)

        outer.addWidget(inner)

    def validate_and_accept(self):
        if not self.input_cust.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter customer name.")
            return
        if not self.input_shop.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter the construction shop name.")
            return
        try:
            qty = int(self.input_qty.text().strip())
            if qty <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid positive quantity.")
            return
        self.accept()

    def get_data(self):
        size_text = self.combo_size.currentText()
        size_code = "XL (Extra Large)" if "XL" in size_text else "L (Large)"
        qty = int(self.input_qty.text().strip() or 0)
        return {
            "customer_name": self.input_cust.text().strip(),
            "shop_name": self.input_shop.text().strip(),
            "block_size": size_code,
            "quantity": qty,
            "sale_date": self.input_date.date().toString("yyyy-MM-dd")
        }


# =============================================================================
# RECORD EXPENSE MODAL
# =============================================================================
class RecordExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Expense")
        self.setFixedSize(440, 460)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(MODAL_BASE_STYLE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_make_top_bar("#EF4444", "#F97316"))

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(26, 20, 26, 22)
        layout.setSpacing(10)

        layout.addLayout(_make_modal_header("Record Expense", self.reject))
        layout.addSpacing(3)

        layout.addWidget(_field_label("Category"))
        self.combo_category = QComboBox()
        self.combo_category.addItems(["Raw Materials", "Maintenance", "Utilities", "Logistics", "Other"])
        layout.addWidget(self.combo_category)

        layout.addWidget(_field_label("Expense Description"))
        self.input_desc = QLineEdit()
        self.input_desc.setPlaceholderText("e.g., Portland cement (50 bags)")
        layout.addWidget(self.input_desc)

        layout.addWidget(_field_label("Amount (PHP)"))
        self.input_amount = QLineEdit()
        self.input_amount.setPlaceholderText("e.g., 2500.00")
        layout.addWidget(self.input_amount)

        layout.addWidget(_field_label("Date Recorded"))
        self.input_date = QDateEdit()
        self.input_date.setDate(QDate.currentDate())
        self.input_date.setCalendarPopup(True)
        self.input_date.setDisplayFormat("MM/dd/yyyy")
        layout.addWidget(self.input_date)

        layout.addSpacing(6)
        self.btn_submit = QPushButton("Save Expense")
        self.btn_submit.setFixedHeight(42)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #DC2626, stop:1 #EF4444);
                color: white; border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #B91C1C, stop:1 #DC2626);
            }
        """)
        self.btn_submit.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.btn_submit)
        outer.addWidget(inner)

    def validate_and_accept(self):
        try:
            clean_str = self.input_amount.text().replace(",", "").replace("₱", "").strip()
            amount = float(clean_str)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid positive amount.")
            return
        if not self.input_desc.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please provide a description.")
            return
        self.accept()

    def get_data(self):
        clean_str = self.input_amount.text().replace(",", "").replace("₱", "").strip()
        return {
            "expense_name": self.input_desc.text().strip() or "Unspecified Expense",
            "amount": float(clean_str or 0.0),
            "category": self.combo_category.currentText(),
            "date_added": self.input_date.date().toString("yyyy-MM-dd")
        }


# =============================================================================
# RECORD STOCK MODAL
# =============================================================================
class RecordStockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Hollowblocks Stock")
        self.setFixedSize(420, 360)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(MODAL_BASE_STYLE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_make_top_bar("#3B82F6", "#8B5CF6"))

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(9)

        layout.addLayout(_make_modal_header("Add Hollowblocks Stock", self.reject))
        layout.addSpacing(3)

        layout.addWidget(_field_label("Hollowblock Size"))
        self.combo_size = QComboBox()
        self.combo_size.addItems(["L (Large) — ₱7/pc", "XL (Extra Large) — ₱8/pc", "None"])
        layout.addWidget(self.combo_size)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)
        col1 = QVBoxLayout()
        col1.setSpacing(6)
        col1.addWidget(_field_label("Quantity (pcs)"))
        self.input_qty = QLineEdit()
        self.input_qty.setPlaceholderText("e.g., 100")
        col1.addWidget(self.input_qty)
        col2 = QVBoxLayout()
        col2.setSpacing(6)
        col2.addWidget(_field_label("Unit"))
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["pcs", "bags", "cubic meters"])
        col2.addWidget(self.combo_unit)
        row_layout.addLayout(col1, stretch=3)
        row_layout.addLayout(col2, stretch=2)
        layout.addLayout(row_layout)

        layout.addSpacing(6)
        self.btn_submit = QPushButton("Save Stock")
        self.btn_submit.setFixedHeight(42)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #2563EB, stop:1 #3B82F6);
                color: white; border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1D4ED8, stop:1 #2563EB);
            }
        """)
        self.btn_submit.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.btn_submit)
        outer.addWidget(inner)

    def validate_and_accept(self):
        try:
            qty = int(self.input_qty.text().strip())
            if qty <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid positive quantity.")
            return
        self.accept()

    def get_data(self):
        selected_size = self.combo_size.currentText()
        db_size = "None"
        price_val = 0.0
        if "XL" in selected_size or "₱8" in selected_size:
            db_size = "XL"
            price_val = 8.0
        elif "L" in selected_size and "XL" not in selected_size:
            db_size = "L"
            price_val = 7.0
        try:
            qty_val = int(self.input_qty.text().strip())
        except ValueError:
            qty_val = 0
        return {
            "size": db_size,
            "quantity": qty_val,
            "unit": self.combo_unit.currentText(),
            "price": price_val,
            "date_added": QDate.currentDate().toString("yyyy-MM-dd")
        }


# =============================================================================
# MAIN INVENTORY WINDOW  (improved UI — no sidebar)
# =============================================================================
class BlockFlowInventory(QWidget):
    def __init__(self, role="owner"):
        super().__init__()
        self.setFont(QFont("Segoe UI", 10))
        self.user_role = role.lower()           # "owner"/"admin" → full access; anything else → staff
        self.setWindowTitle("BlockFlow — Inventory Management")
        self.network_manager = QNetworkAccessManager(self)
        self.current_tab = "sales"
        self.expense_records = []
        self.inventory_records = []
        self.sales_records = []

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(current_dir, "image_b08741.png")
        if not os.path.exists(self.image_path):
            self.image_path = os.path.join(current_dir, "image_b08741.jpg")

        self.init_ui()
        self.setWindowOpacity(0.0)
        self.showFullScreen()
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(500)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
        self.fetch_expenses_async()
        self.fetch_inventory_async()
        self.fetch_sales_async()

    # ── Background painting ──────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#060B18"))
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
            painter.fillRect(self.rect(), QColor(4, 8, 20, 210))
        painter.end()

    def init_ui(self):
        self.setStyleSheet("background-color: transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ══════════════════════════════════════════════════════════════
        # TOP NAV BAR  (replaces sidebar)
        # ══════════════════════════════════════════════════════════════
        nav_bar = QFrame()
        nav_bar.setFixedHeight(64)
        nav_bar.setObjectName("NavBar")
        nav_bar.setStyleSheet("""
            QFrame#NavBar {
                background-color: rgba(6, 10, 22, 230);
                border-bottom: 1px solid rgba(255,255,255,8);
            }
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(28, 0, 28, 0)
        nav_layout.setSpacing(0)

        # Brand
        brand_badge = QLabel("BF")
        brand_badge.setFixedSize(34, 34)
        brand_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_badge.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        brand_badge.setStyleSheet("""
            color: white;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3B82F6,stop:1 #8B5CF6);
            border-radius: 9px;
        """)
        brand_label = QLabel("BlockFlow")
        brand_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        brand_label.setStyleSheet("color: #F1F5F9; padding-left: 10px; letter-spacing: 0.3px;")

        nav_layout.addWidget(brand_badge)
        nav_layout.addWidget(brand_label)
        nav_layout.addSpacing(36)

        # Separator
        sep = QFrame()
        sep.setFixedSize(1, 28)
        sep.setStyleSheet("background-color: rgba(255,255,255,10);")
        nav_layout.addWidget(sep)
        nav_layout.addSpacing(28)

        # Nav buttons — Dashboard only visible to admin/owner
        self.btn_nav_inv = self._nav_button("Inventory", True)

        is_admin = self.user_role in ("owner", "admin")
        if is_admin:
            self.btn_nav_dash = self._nav_button("Dashboard", False)
            self.btn_nav_dash.clicked.connect(self.handle_nav_dashboard)
            nav_layout.addWidget(self.btn_nav_dash)
            nav_layout.addSpacing(4)

        nav_layout.addWidget(self.btn_nav_inv)
        if is_admin:
            self.btn_nav_analytics = self._nav_button("Analytics", False)
            self.btn_nav_analytics.clicked.connect(self.handle_nav_analytics)
            nav_layout.addSpacing(4)
            nav_layout.addWidget(self.btn_nav_analytics)
        nav_layout.addStretch()

        # Right side — user badge + logout
        badge_label = "👤  Admin" if is_admin else "👷  Staff"
        user_badge = QLabel(badge_label)
        user_badge.setStyleSheet("""
            color: #CBD5E1;
            background-color: rgba(30,41,59,180);
            padding: 7px 16px;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,10);
            font-weight: 600;
            font-size: 13px;
        """)

        btn_logout_top = QPushButton("Logout")
        btn_logout_top.setFixedHeight(34)
        btn_logout_top.setStyleSheet("""
            QPushButton {
                color: #94A3B8;
                background-color: rgba(30,41,59,160);
                padding: 0 18px;
                border-radius: 17px;
                border: 1px solid rgba(255,255,255,10);
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(239,68,68,0.18);
                border-color: rgba(239,68,68,0.35);
                color: #F87171;
            }
        """)
        btn_logout_top.clicked.connect(self.handle_logout)

        nav_layout.addWidget(user_badge)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(btn_logout_top)

        root.addWidget(nav_bar)

        # ══════════════════════════════════════════════════════════════
        # MAIN CONTENT
        # ══════════════════════════════════════════════════════════════
        content_area = QWidget()
        content_area.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.setSpacing(16)

        # ── Page title ───────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        page_title = QLabel("Inventory")
        page_title.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        page_title.setStyleSheet("color: #F8FAFC; letter-spacing: -0.5px;")

        page_sub = QLabel("Track hollowblocks stock, sales, and business expenses")
        page_sub.setStyleSheet("color: #B8C5D6; font-size: 13px;")

        title_col.addWidget(page_title)
        title_col.addWidget(page_sub)
        title_row.addLayout(title_col)
        title_row.addStretch()

        # Date pill
        date_lbl = QLabel(QDate.currentDate().toString("MMMM d, yyyy"))
        date_lbl.setStyleSheet("""
            color: #CBD5E1;
            background-color: rgba(15, 23, 42, 180);
            padding: 8px 16px;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,8);
            font-size: 12px;
            font-weight: 600;
        """)
        title_row.addWidget(date_lbl)
        content_layout.addLayout(title_row)

        # ── Action cards ─────────────────────────────────────────────
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_expense = self._create_action_card(
            "📋", "Record Expense", "Log materials, maintenance, and operating costs",
            "#EF4444", "rgba(239,68,68,0.12)", "rgba(239,68,68,0.22)")
        self.card_expense.mousePressEvent = lambda e: self.switch_tab("expenses")

        self.card_stock = self._create_action_card(
            "📦", "Add Hollowblocks Stock", "Increase the available inventory",
            "#3B82F6", "rgba(59,130,246,0.12)", "rgba(59,130,246,0.22)")
        self.card_stock.mousePressEvent = lambda e: self.switch_tab("stock")

        self.card_sales = self._create_action_card(
            "💰", "Record Sale", "Log a customer order and payment",
            "#10B981", "rgba(16,185,129,0.12)", "rgba(16,185,129,0.22)")
        self.card_sales.mousePressEvent = lambda e: self.switch_tab("sales")

        cards_layout.addWidget(self.card_expense)
        cards_layout.addWidget(self.card_stock)
        cards_layout.addWidget(self.card_sales)
        content_layout.addLayout(cards_layout)

        # ── Table toolbar ─────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.table_title = QLabel("Sales Records")
        self.table_title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        self.table_title.setStyleSheet("color: #F1F5F9;")

        # Search bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search records...")
        self.search_box.setFixedHeight(38)
        self.search_box.setFixedWidth(240)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: rgba(15, 23, 42, 200);
                color: #CBD5E1;
                border: 1px solid rgba(255,255,255,10);
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
            }
            QLineEdit::placeholder { color: #94A3B8; }
            QLineEdit:focus {
                border: 1px solid rgba(59,130,246,0.5);
                background-color: rgba(15, 23, 42, 240);
            }
        """)
        self.search_box.textChanged.connect(self.filter_table)

        self.btn_add_action = QPushButton("+ Record Sale")
        self.btn_add_action.setFixedHeight(38)
        self.btn_add_action.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #059669, stop:1 #10B981);
                color: white; padding: 0 22px;
                font-weight: bold; border-radius: 10px; border: none; font-size: 13px;
                letter-spacing: 0.2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #047857, stop:1 #059669);
            }
            QPushButton:pressed { background-color: #047857; }
        """)
        self.btn_add_action.clicked.connect(self.handle_add_action_click)

        toolbar.addWidget(self.table_title)
        toolbar.addStretch()
        toolbar.addWidget(self.search_box)
        toolbar.addWidget(self.btn_add_action)
        content_layout.addLayout(toolbar)

        # ── Data table ────────────────────────────────────────────────
        table_wrapper = QFrame()
        table_wrapper.setObjectName("TableWrapper")
        table_wrapper.setStyleSheet("""
            QFrame#TableWrapper {
                background-color: rgba(6, 10, 22, 175);
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,10);
            }
        """)
        wrapper_layout = QVBoxLayout(table_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border-radius: 16px;
                border: none;
                gridline-color: rgba(255,255,255,5);
                color: #E2E8F0;
                font-size: 13px;
                font-weight: 500;
            }
            QTableWidget::item {
                padding: 10px 16px;
                border: none;
                color: #E2E8F0;
            }
            QTableWidget::item:selected {
                background-color: rgba(59,130,246,0.20);
                color: #FFFFFF;
            }
            QTableWidget::item:alternate {
                background-color: rgba(255,255,255,3);
            }
            QHeaderView::section {
                background-color: rgba(3, 6, 16, 230);
                color: #AEBBCD;
                padding: 14px 16px;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1.4px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,10);
                text-transform: uppercase;
            }
            QHeaderView::section:first {
                border-top-left-radius: 16px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 16px;
            }
            QScrollBar:vertical {
                background: transparent; width: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,20); border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        wrapper_layout.addWidget(self.table)
        content_layout.addWidget(table_wrapper)

        root.addWidget(content_area)
        self.switch_tab("sales")

    # ── Nav button helper ──────────────────────────────────────────────────────
    def _nav_button(self, text, active=False):
        btn = QPushButton(text)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(59,130,246,0.15);
                    color: #93C5FD;
                    border: none;
                    border-radius: 8px;
                    padding: 0 18px;
                    font-size: 13px;
                    font-weight: 700;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94A3B8;
                    border: none;
                    border-radius: 8px;
                    padding: 0 18px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,6);
                    color: #CBD5E1;
                }
            """)
        return btn

    # ── Action card helper ─────────────────────────────────────────────────────
    def _create_action_card(self, icon, title, description, accent, bg_normal, bg_active):
        card = QFrame()
        card.setMinimumHeight(132)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setObjectName("ActionCard")
        card._accent = accent
        card._bg_normal = bg_normal
        card._bg_active = bg_active
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_normal};
                border-radius: 14px;
                border: 1px solid rgba(255,255,255,8);
            }}
            QFrame:hover {{
                background-color: {bg_active};
                border: 1px solid {accent};
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(8)

        # Icon + accent dot row
        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 20))
        icon_lbl.setStyleSheet("background: transparent; border: none;")

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background-color: {accent}; border-radius: 4px;")
        top_row.addWidget(icon_lbl)
        top_row.addStretch()
        top_row.addWidget(dot)
        layout.addLayout(top_row)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: #FFFFFF; border: none;")

        lbl_desc = QLabel(description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setMinimumHeight(30)
        lbl_desc.setStyleSheet("color: #C3CFDD; font-size: 12px; border: none;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        return card

    # ── Tab switching ──────────────────────────────────────────────────────────
    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        self.search_box.clear()

        # Reset all cards
        for card, accent, bg in [
            (self.card_expense, "#EF4444", "rgba(239,68,68,0.10)"),
            (self.card_stock,   "#3B82F6", "rgba(59,130,246,0.10)"),
            (self.card_sales,   "#10B981", "rgba(16,185,129,0.10)"),
        ]:
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg};
                    border-radius: 14px;
                    border: 1px solid rgba(255,255,255,8);
                }}
                QFrame:hover {{
                    background-color: rgba(255,255,255,0.06);
                    border: 1px solid {accent};
                }}
            """)

        def activate_card(card, accent, bg_active):
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_active};
                    border-radius: 14px;
                    border: 2px solid {accent};
                }}
            """)

        if tab_name == "expenses":
            activate_card(self.card_expense, "#EF4444", "rgba(239,68,68,0.25)")
            self.table_title.setText("Expense Records")
            self.btn_add_action.setText("+ Record Expense")
            self.btn_add_action.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #DC2626, stop:1 #EF4444);
                    color: white; padding: 0 22px;
                    font-weight: bold; border-radius: 10px; border: none; font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #B91C1C, stop:1 #DC2626);
                }
            """)
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["DATE", "CATEGORY", "DESCRIPTION", "AMOUNT"])

        elif tab_name == "stock":
            activate_card(self.card_stock, "#3B82F6", "rgba(59,130,246,0.25)")
            self.table_title.setText("Hollowblocks Stock Records")
            self.btn_add_action.setText("+ Add Stock")
            self.btn_add_action.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #2563EB, stop:1 #3B82F6);
                    color: white; padding: 0 22px;
                    font-weight: bold; border-radius: 10px; border: none; font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #1D4ED8, stop:1 #2563EB);
                }
            """)
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(
                ["SIZE", "QUANTITY", "UNIT", "DATE ADDED"]
            )

        elif tab_name == "sales":
            activate_card(self.card_sales, "#10B981", "rgba(16,185,129,0.25)")
            self.table_title.setText("Sales Records")
            self.btn_add_action.setText("+ Record Sale")
            self.btn_add_action.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #059669, stop:1 #10B981);
                    color: white; padding: 0 22px;
                    font-weight: bold; border-radius: 10px; border: none; font-size: 13px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #047857, stop:1 #059669);
                }
            """)
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(
                ["DATE", "CUSTOMER NAME", "SHOP NAME", "PRODUCT SIZE", "QUANTITY", "TOTAL AMOUNT"])

        self.refresh_table()

    def handle_add_action_click(self):
        if self.current_tab == "expenses":
            self.open_record_expense_modal()
        elif self.current_tab == "stock":
            self.open_record_stock_modal()
        elif self.current_tab == "sales":
            self.open_record_sales_modal()

    # ── Search / filter ───────────────────────────────────────────────────────
    def filter_table(self, query):
        query = query.strip().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match if query else False)

    # ── Async API calls ───────────────────────────────────────────────────────
    def fetch_sales_async(self):
        request = QNetworkRequest(QUrl(f"{BASE_API_URL}/sales"))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.on_sales_fetched(reply))

    def on_sales_fetched(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(bytes(reply.readAll()).decode('utf-8'))
                loaded = []
                for item in data:
                    date_val = str(item.get("sale_date") or "N/A")
                    cust = str(item.get("customer_name") or "N/A")
                    shop = str(item.get("shop_name") or "N/A")
                    size = str(item.get("block_size") or "L (Large)")
                    try:
                        qty_num = int(item.get("quantity", 0))
                    except (ValueError, TypeError):
                        qty_num = 0
                    total_calc = float(item.get("total_amount") or 0)
                    if total_calc <= 0:
                        unit_price = 8.0 if "XL" in size.upper() else 7.0
                        total_calc = qty_num * unit_price
                    loaded.append([date_val, cust, shop, size, f"{qty_num:,} pcs", f"₱{total_calc:,.0f}"])
                self.sales_records = loaded
            except Exception as e:
                print(f"Sales JSON parse error: {e}")
                self.sales_records = []
        else:
            self.sales_records = []
        reply.deleteLater()
        if self.current_tab == "sales":
            self.refresh_table()

    def fetch_expenses_async(self):
        request = QNetworkRequest(QUrl(f"{BASE_API_URL}/expenses"))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.on_expenses_fetched(reply))

    def on_expenses_fetched(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(bytes(reply.readAll()).decode('utf-8'))
                loaded = []
                for item in data:
                    date_val = item.get("date_added", "N/A")
                    cat = item.get("category", "Raw Material")
                    desc = item.get("expense_name") or item.get("description", "")
                    try:
                        amt = float(item.get("amount", 0))
                    except (ValueError, TypeError):
                        amt = 0.0
                    loaded.append([date_val, cat, desc, f"₱{amt:,.2f}"])
                self.expense_records = loaded
            except Exception as e:
                print(f"Expense JSON parse error: {e}")
                self.expense_records = []
        else:
            self.expense_records = []
        reply.deleteLater()
        if self.current_tab == "expenses":
            self.refresh_table()

    def fetch_inventory_async(self):
        request = QNetworkRequest(QUrl(f"{BASE_API_URL}/inventory"))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.on_inventory_fetched(reply))

    def on_inventory_fetched(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(bytes(reply.readAll()).decode('utf-8'))
                loaded = []
                for item in data:
                    size = item.get("size", "None")
                    try:
                        qty = int(item.get("quantity", 0))
                    except (ValueError, TypeError):
                        qty = 0
                    unit = item.get("unit", "pcs")
                    date_added = item.get("date_added", "N/A")
                    loaded.append([size, str(qty), unit, date_added])
                self.inventory_records = loaded
            except Exception as e:
                print(f"Inventory JSON parse error: {e}")
                self.inventory_records = []
        else:
            self.inventory_records = []
        reply.deleteLater()
        if self.current_tab == "stock":
            self.refresh_table()

    def refresh_table(self):
        if self.current_tab == "expenses":
            records = self.expense_records
        elif self.current_tab == "stock":
            records = self.inventory_records
        else:
            records = self.sales_records

        self.table.setRowCount(len(records))
        for row_idx, row_data in enumerate(records):
            for col_idx, cell_value in enumerate(row_data):
                item = QTableWidgetItem(str(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                is_amount_col = (
                    (self.current_tab == "expenses" and col_idx == 3) or
                    (self.current_tab == "sales" and col_idx == 5)
                )
                if is_amount_col:
                    item.setForeground(QColor("#34D399") if self.current_tab == "sales" else QColor("#F87171"))
                    item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                self.table.setItem(row_idx, col_idx, item)

    # ── Modal launchers ───────────────────────────────────────────────────────
    def open_record_sales_modal(self):
        dialog = RecordSalesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            payload = json.dumps(data).encode('utf-8')
            request = QNetworkRequest(QUrl(f"{BASE_API_URL}/sales"))
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            reply = self.network_manager.post(request, payload)
            reply.finished.connect(lambda: self._on_post_done(reply, self.fetch_sales_async))

    def open_record_expense_modal(self):
        dialog = RecordExpenseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            payload = json.dumps(data).encode('utf-8')
            request = QNetworkRequest(QUrl(f"{BASE_API_URL}/expenses"))
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            reply = self.network_manager.post(request, payload)
            reply.finished.connect(lambda: self._on_post_done(reply, self.fetch_expenses_async))

    def open_record_stock_modal(self):
        dialog = RecordStockDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            payload = json.dumps(data).encode('utf-8')
            request = QNetworkRequest(QUrl(f"{BASE_API_URL}/inventory"))
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            reply = self.network_manager.post(request, payload)
            reply.finished.connect(lambda: self._on_post_done(reply, self.fetch_inventory_async))

    def _on_post_done(self, reply: QNetworkReply, refresh_fn):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            QMessageBox.critical(self, "Save Failed", reply.errorString())
        else:
            raw_body = bytes(reply.readAll()).decode("utf-8", errors="replace")
            try:
                response_data = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                response_data = {}
            if reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) not in (
                200,
                201,
            ):
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    response_data.get("detail", "The server rejected this record."),
                )
            else:
                refresh_fn()
        reply.deleteLater()

    def handle_nav_dashboard(self):
        try:
            from dashboard_view import BlockFlowDashboard
            self.dash_window = BlockFlowDashboard()
            self.dash_window.show()
            self.close()
        except ImportError:
            pass

    def handle_nav_analytics(self):
        try:
            from analytics_view import BlockFlowAnalytics
            self.analytics_window = BlockFlowAnalytics(role=self.user_role)
            self.analytics_window.show()
            self.close()
        except ImportError:
            pass

    def handle_logout(self):
        try:
            from login_view import BlockFlowLogin
            self.login_window = BlockFlowLogin()
            self.login_window.show()
            self.close()
        except ImportError:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BlockFlowInventory()
    window.show()
    sys.exit(app.exec())
