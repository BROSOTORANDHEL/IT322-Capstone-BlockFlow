import sys
import requests
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem, 
    QHeaderView, QDialog, QComboBox, QLineEdit, QDateEdit, QMessageBox
)

# -------------------------------------------------------------------------
# RECORD EXPENSE MODAL DIALOG
# -------------------------------------------------------------------------
class RecordExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Expense")
        self.setFixedSize(400, 450)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 2px solid #334155;
                border-radius: 12px;
            }
            QLabel {
                color: #94A3B8;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox, QLineEdit, QDateEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E293B;
                color: #F8FAFC;
                selection-background-color: #334155;
            }
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(15)

        title_layout = QHBoxLayout()
        title_label = QLabel("Record Expense")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #F8FAFC; font-size: 18px;")
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #94A3B8; border: none; font-size: 16px;
            }
            QPushButton:hover { color: #EF4444; }
        """)
        btn_close.clicked.connect(self.reject)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(btn_close)
        layout.addLayout(title_layout)

        # Category
        lbl_category = QLabel("Category")
        self.combo_category = QComboBox()
        self.combo_category.addItems(["Raw Material", "Maintenance", "Utilities", "Logistics", "Others"])
        layout.addWidget(lbl_category)
        layout.addWidget(self.combo_category)

        # Description
        lbl_desc = QLabel("Description")
        self.input_desc = QLineEdit()
        self.input_desc.setPlaceholderText("e.g., Portland Cement (50 bags)")
        layout.addWidget(lbl_desc)
        layout.addWidget(self.input_desc)

        # Amount
        lbl_amount = QLabel("Amount (₱)")
        self.input_amount = QLineEdit()
        self.input_amount.setPlaceholderText("0.00")
        layout.addWidget(lbl_amount)
        layout.addWidget(self.input_amount)

        # Date
        lbl_date = QLabel("Date")
        self.input_date = QDateEdit()
        self.input_date.setDate(QDate.currentDate())
        self.input_date.setCalendarPopup(True)
        self.input_date.setDisplayFormat("MM/dd/yyyy") 
        layout.addWidget(lbl_date)
        layout.addWidget(self.input_date)

        layout.addSpacing(10)

        self.btn_submit = QPushButton("Add Expense")
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        self.btn_submit.clicked.connect(self.accept)
        layout.addWidget(self.btn_submit)

    def get_data(self):
        try:
            clean_amount_str = self.input_amount.text().replace(",", "").replace("₱", "").replace("-", "").strip()
            raw_amount = float(clean_amount_str or 0.0)
        except ValueError:
            raw_amount = 0.0

        return {
            "expense_name": self.input_desc.text().strip() or "Unspecified Expense",
            "amount": raw_amount,
            "category": self.combo_category.currentText(),
            "date_added": self.input_date.date().toString("yyyy-MM-dd")
        }


# -------------------------------------------------------------------------
# MAIN INVENTORY WINDOW (DYNAMIC DATABASE INTEGRATION)
# -------------------------------------------------------------------------
class BlockFlowInventory(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlockFlow - Inventory Management")
        self.init_ui()
        self.showFullScreen()
        
        # Load real database data from the API tables on startup
        self.load_live_database_records()

    def init_ui(self):
        self.setStyleSheet("background-color: #0F172A;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar Navigation
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #1E293B; border-right: 1px solid #334155;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 40)
        sidebar_layout.setSpacing(15)

        logo_label = QLabel("BlockFlow")
        logo_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        logo_label.setStyleSheet("color: #F8FAFC;")
        sidebar_layout.addWidget(logo_label)

        sub_logo = QLabel("Magalin Trading")
        sub_logo.setFont(QFont("Arial", 10))
        sub_logo.setStyleSheet("color: #94A3B8; margin-bottom: 20px;")
        sidebar_layout.addWidget(sub_logo)

        btn_dash = QPushButton("  Dashboard")
        btn_inv = QPushButton("  Inventory")
        btn_analytics = QPushButton("  Analytics")

        nav_style = """
            QPushButton {
                background-color: transparent; color: #94A3B8; font-size: 14px;
                text-align: left; padding: 12px; border: none; border-radius: 8px;
            }
            QPushButton:hover { background-color: #334155; color: #F8FAFC; }
        """
        btn_dash.setStyleSheet(nav_style)
        btn_analytics.setStyleSheet(nav_style)
        
        btn_inv.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: #F8FAFC; font-size: 14px;
                text-align: left; padding: 12px; border: none; border-radius: 8px;
                font-weight: bold;
            }
        """)

        sidebar_layout.addWidget(btn_dash)
        sidebar_layout.addWidget(btn_inv)
        sidebar_layout.addWidget(btn_analytics)
        sidebar_layout.addStretch()

        # Content Area
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(25)

        header_layout = QHBoxLayout()
        header_title = QLabel("Inventory")
        header_title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #F8FAFC;")
        
        user_badge = QLabel("👤 Staff Member")
        user_badge.setStyleSheet("color: #F8FAFC; background-color: #1E293B; padding: 8px 15px; border-radius: 20px;")
        
        btn_logout = QPushButton("Logout")
        btn_logout.setStyleSheet("""
            QPushButton { background-color: #334155; color: #F8FAFC; padding: 8px 16px; border-radius: 6px; border: 1px solid #475569; }
            QPushButton:hover { background-color: #EF4444; border-color: #EF4444; }
        """)
        btn_logout.clicked.connect(self.handle_logout)

        header_layout.addWidget(header_title)
        header_layout.addStretch()
        header_layout.addWidget(user_badge)
        header_layout.addWidget(btn_logout)
        content_layout.addLayout(header_layout)

        cards_layout = QHBoxLayout()
        
        self.card_expense = self.create_action_card("Record Expenses", "Raw materials, maintenance, other", "#EF4444")
        self.card_expense.mousePressEvent = lambda event: self.open_record_expense_modal()
        
        card_stock = self.create_action_card("Record Stock", "Add new stock to inventory", "#3B82F6")
        card_sales = self.create_action_card("Record Sales", "Daily sales transactions", "#10B981")
        
        cards_layout.addWidget(self.card_expense)
        cards_layout.addWidget(card_stock)
        cards_layout.addWidget(card_sales)
        content_layout.addLayout(cards_layout)

        table_header_layout = QHBoxLayout()
        table_title = QLabel("Expense Records")
        table_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        table_title.setStyleSheet("color: #F8FAFC;")
        
        btn_add_expense = QPushButton("+ Add Expense")
        btn_add_expense.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px; border: none;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        btn_add_expense.clicked.connect(self.open_record_expense_modal)
        
        table_header_layout.addWidget(table_title)
        table_header_layout.addStretch()
        table_header_layout.addWidget(btn_add_expense)
        content_layout.addLayout(table_header_layout)

        # Expense Table Visuals
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["DATE", "CATEGORY", "DESCRIPTION", "AMOUNT"])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(30, 41, 59, 150);
                border-radius: 8px;
                gridline-color: #334155;
                color: #F8FAFC;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.expense_records = []
        content_layout.addWidget(self.table)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area)

    def create_action_card(self, title, description, border_color):
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1E293B;
                border-radius: 12px;
                border: 1px solid #334155;
            }}
            QFrame:hover {{
                border: 1px solid {border_color};
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #F8FAFC; border: none;")
        
        lbl_desc = QLabel(description)
        lbl_desc.setFont(QFont("Arial", 10))
        lbl_desc.setStyleSheet("color: #94A3B8; border: none;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        return card

    # --- DYNAMIC API INTEGRATION ---
    def load_live_database_records(self):
        """Fetches live entries from database table using schema mapping to support old & new db formats."""
        try:
            response = requests.get("http://127.0.0.1:8000/api/expenses")
            if response.status_code == 200:
                expenses_data = response.json()
                
                loaded_expenses = []
                for item in expenses_data:
                    # 1. Map Date column: looks for date_recorded or date_added
                    date_val = item.get("date_recorded", item.get("date_added", ""))
                    if not date_val:
                        date_val = "2026-07-15"
                        
                    # 2. Map Category column
                    category_val = item.get("category", "Raw Material")
                    
                    # 3. Map Description column: looks for description or expense_name
                    desc_val = item.get("description", item.get("expense_name", "Unspecified Expense"))
                    
                    # 4. Map Amount column
                    try:
                        amount_val = float(item.get("amount", 0.0))
                    except (ValueError, TypeError):
                        amount_val = 0.0
                        
                    formatted_amount = f"-₱{amount_val:,.2f}"
                    
                    loaded_expenses.append([date_val, category_val, desc_val, formatted_amount])
                
                # Assign mapped API records to our UI tracking list
                self.expense_records = loaded_expenses
            else:
                self.load_mock_fallbacks()
        except requests.exceptions.ConnectionError:
            self.load_mock_fallbacks()
            
        # Ensure list entries are sorted chronological (newest at the top)
        self.expense_records.sort(key=lambda x: x[0], reverse=True)
        self.refresh_table()

    def load_mock_fallbacks(self):
        """Standard mock defaults if connection to the local server drops."""
        self.expense_records = [
            ["2026-01-08", "Raw Material", "Portland Cement (50 bags)", "-₱12,500.00"],
            ["2026-01-20", "Maintenance", "Mixer Repair", "-₱2,500.00"],
            ["2026-02-10", "Raw Material", "Screened Sand (10 cubic meters)", "-₱8,000.00"]
        ]

    def refresh_table(self):
        self.table.setRowCount(len(self.expense_records))
        for row_idx, row_data in enumerate(self.expense_records):
            for col_idx, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if col_idx == 3:
                    item.setForeground(QColor("#EF4444"))
                self.table.setItem(row_idx, col_idx, item)

    def open_record_expense_modal(self):
        dialog = RecordExpenseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_expense_payload = dialog.get_data()
            
            try:
                api_endpoint = "http://127.0.0.1:8000/api/expenses" 
                response = requests.post(api_endpoint, json=new_expense_payload)
                
                if response.status_code in [200, 201]:
                    # Instantly re-request the list to pull the exact newly generated item from database
                    self.load_live_database_records()
                else:
                    QMessageBox.warning(
                        self, "Save Error", 
                        f"Database rejected entry!\nStatus: {response.status_code}\nServer Info: {response.text}"
                    )
            except requests.exceptions.ConnectionError:
                QMessageBox.critical(
                    self, "Connection Lost", 
                    "Could not connect to database server.\nPlease ensure your backend API is running!"
                )

    def handle_logout(self):
        try:
            from login_view import BlockFlowLogin
            self.login_window = BlockFlowLogin()
            self.login_window.show()
            self.close()
        except ImportError:
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BlockFlowInventory()
    window.show()
    sys.exit(app.exec())