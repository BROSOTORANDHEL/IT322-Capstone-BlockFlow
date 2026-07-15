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
# RECORD STOCK MODAL DIALOG
# -------------------------------------------------------------------------
class RecordStockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record New Stock")
        self.setFixedSize(400, 500)
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
            QComboBox, QLineEdit {
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
        title_label = QLabel("Record New Stock")
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

        # Item Name
        lbl_name = QLabel("Item Name")
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g., Standard Hollow Blocks")
        layout.addWidget(lbl_name)
        layout.addWidget(self.input_name)

        # Size 
        lbl_size = QLabel("Size")
        self.combo_size = QComboBox()
        self.combo_size.addItems([
            "L (Large) - ₱7/pc",
            "XL (Extra Large) - ₱8/pc",
            "None"
        ])
        layout.addWidget(lbl_size)
        layout.addWidget(self.combo_size)

        # Quantity
        lbl_qty = QLabel("Quantity")
        self.input_qty = QLineEdit()
        self.input_qty.setPlaceholderText("Enter quantity (e.g., 100)")
        layout.addWidget(lbl_qty)
        layout.addWidget(self.input_qty)

        # Unit
        lbl_unit = QLabel("Unit")
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["pcs", "bags", "cubic meters"])
        layout.addWidget(lbl_unit)
        layout.addWidget(self.combo_unit)

        layout.addSpacing(10)

        self.btn_submit = QPushButton("Record Stock")
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        self.btn_submit.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.btn_submit)

    def validate_and_accept(self):
        if not self.input_name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an item name.")
            return
            
        try:
            qty = int(self.input_qty.text().strip())
            if qty < 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid non-negative quantity.")
            return

        self.accept()

    def get_data(self):
        selected_size = self.combo_size.currentText()
        
        # Maps frontend selection variables down to database-compliant string structures
        db_size = "None"
        price_val = 0.0
        
        if "L (Large)" in selected_size or "₱7" in selected_size:
            db_size = "L"
            price_val = 7.0
        elif "XL (Extra Large)" in selected_size or "₱8" in selected_size:
            db_size = "XL"
            price_val = 8.0
        else:
            db_size = "None"
            price_val = 0.0

        try:
            qty_val = int(self.input_qty.text().strip())
        except ValueError:
            qty_val = 0

        # Build structural clean schema payload keys to pass cleanly to database
        return {
            "item_name": self.input_name.text().strip() or "Unnamed Item",
            "size": db_size,          
            "item_size": db_size,     
            "Size": db_size,          
            "quantity": qty_val,
            "unit": self.combo_unit.currentText(),
            "price": price_val,
            "date_added": QDate.currentDate().toString("yyyy-MM-dd"),
            "date_recorded": QDate.currentDate().toString("yyyy-MM-dd")
        }


# -------------------------------------------------------------------------
# MAIN INVENTORY WINDOW
# -------------------------------------------------------------------------
class BlockFlowInventory(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlockFlow - Inventory Management")
        
        self.current_tab = "expenses"
        self.inventory_records = []
        self.expense_records = []
        
        self.init_ui()
        self.showFullScreen()
        
        self.load_live_database_records()
        self.load_live_inventory_records()

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
        self.card_expense.mousePressEvent = lambda event: self.switch_tab("expenses")
        
        self.card_stock = self.create_action_card("Record Stock", "Add new stock to inventory", "#3B82F6")
        self.card_stock.mousePressEvent = lambda event: self.switch_tab("stock")
        
        card_sales = self.create_action_card("Record Sales", "Daily sales transactions", "#10B981")
        
        cards_layout.addWidget(self.card_expense)
        cards_layout.addWidget(self.card_stock)
        cards_layout.addWidget(card_sales)
        content_layout.addLayout(cards_layout)

        table_header_layout = QHBoxLayout()
        self.table_title = QLabel("Expense Records")
        self.table_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.table_title.setStyleSheet("color: #F8FAFC;")
        
        self.btn_add_action = QPushButton("+ Add Expense")
        self.btn_add_action.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px; border: none;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        self.btn_add_action.clicked.connect(self.handle_add_action_click)
        
        table_header_layout.addWidget(self.table_title)
        table_header_layout.addStretch()
        table_header_layout.addWidget(self.btn_add_action)
        content_layout.addLayout(table_header_layout)

        # Records Table Visuals
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
        content_layout.addWidget(self.table)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area)

        self.switch_tab("expenses")

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

    # --- VIEW SWITCHING / TAB LOGIC ---
    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        
        if tab_name == "expenses":
            self.card_expense.setStyleSheet("""
                QFrame { background-color: #1E293B; border-radius: 12px; border: 2px solid #EF4444; }
            """)
            self.card_stock.setStyleSheet("""
                QFrame { background-color: #1E293B; border-radius: 12px; border: 1px solid #334155; }
                QFrame:hover { border: 1px solid #3B82F6; }
            """)
            
            self.table_title.setText("Expense Records")
            self.btn_add_action.setText("+ Add Expense")
            self.btn_add_action.setStyleSheet("""
                QPushButton { background-color: #EF4444; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px; border: none; }
                QPushButton:hover { background-color: #DC2626; }
            """)
            
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["DATE", "CATEGORY", "DESCRIPTION", "AMOUNT"])
            
        elif tab_name == "stock":
            self.card_stock.setStyleSheet("""
                QFrame { background-color: #1E293B; border-radius: 12px; border: 2px solid #3B82F6; }
            """)
            self.card_expense.setStyleSheet("""
                QFrame { background-color: #1E293B; border-radius: 12px; border: 1px solid #334155; }
                QFrame:hover { border: 1px solid #EF4444; }
            """)
            
            self.table_title.setText("Record Stock")
            self.btn_add_action.setText("+ Record Stock")
            self.btn_add_action.setStyleSheet("""
                QPushButton { background-color: #3B82F6; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px; border: none; }
                QPushButton:hover { background-color: #2563EB; }
            """)
            
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["ITEM NAME", "SIZE", "QUANTITY", "UNIT", "DATE ADDED"])

        self.refresh_table()

    def handle_add_action_click(self):
        if self.current_tab == "expenses":
            self.open_record_expense_modal()
        elif self.current_tab == "stock":
            self.open_record_stock_modal()

    # --- DYNAMIC API INTEGRATION ---
    def load_live_database_records(self):
        try:
            response = requests.get("http://127.0.0.1:8000/api/expenses")
            if response.status_code == 200:
                expenses_data = response.json()
                
                loaded_expenses = []
                for item in expenses_data:
                    date_val = item.get("date_added", item.get("date_recorded", "2026-07-15"))
                    category_val = item.get("category", "Raw Material")
                    desc_val = item.get("expense_name", item.get("description", "Unspecified Expense"))
                    
                    try:
                        amount_val = float(item.get("amount", 0.0))
                    except (ValueError, TypeError):
                        amount_val = 0.0
                        
                    formatted_amount = f"-₱{amount_val:,.2f}"
                    loaded_expenses.append([date_val, category_val, desc_val, formatted_amount])
                
                self.expense_records = loaded_expenses
            else:
                self.load_mock_fallbacks()
        except requests.exceptions.ConnectionError:
            self.load_mock_fallbacks()
            
        self.expense_records.sort(key=lambda x: x[0], reverse=True)
        if self.current_tab == "expenses":
            self.refresh_table()

    def load_live_inventory_records(self):
        try:
            response = requests.get("http://127.0.0.1:8000/api/inventory")
            if response.status_code == 200:
                inventory_data = response.json()
                
                loaded_inventory = []
                for item in inventory_data:
                    name = item.get("item_name", "Unknown Item")
                    qty = item.get("quantity", 0)
                    price = item.get("price", 0.0)
                    date_added = item.get("date_added", item.get("date_recorded", "2026-07-15"))
                    
                    # Fix: Priority given to the raw saved DB size values!
                    size_val = item.get("size")
                    if not size_val or size_val in ["None", "null", "None (Value)"]:
                        if price == 7.0:
                            size_val = "L"
                        elif price == 8.0:
                            size_val = "XL"
                        else:
                            size_val = "None"
                    
                    unit_val = item.get("unit", "pcs")
                    loaded_inventory.append([name, size_val, f"{qty:,}", unit_val, date_added])
                
                self.inventory_records = loaded_inventory
            else:
                self.load_inventory_fallbacks()
        except requests.exceptions.ConnectionError:
            self.load_inventory_fallbacks()
            
        if self.current_tab == "stock":
            self.refresh_table()

    def load_mock_fallbacks(self):
        self.expense_records = [
            ["2026-01-08", "Raw Material", "Portland Cement (50 bags)", "-₱12,500.00"],
            ["2026-01-20", "Maintenance", "Mixer Repair", "-₱2,500.00"],
            ["2026-02-10", "Raw Material", "Screened Sand (10 cubic meters)", "-₱8,000.00"]
        ]

    def load_inventory_fallbacks(self):
        self.inventory_records = [
            ["L Hollow Blocks", "L", "8,500", "pcs", "2026-04-28"],
            ["XL Hollow Blocks", "XL", "4,200", "pcs", "2026-04-28"]
        ]

    def refresh_table(self):
        self.table.setRowCount(0) # Deep reset grid lines before drawing to ensure sync
        self.table.clearContents()
        
        if self.current_tab == "expenses":
            self.table.setRowCount(len(self.expense_records))
            for row_idx, row_data in enumerate(self.expense_records):
                for col_idx, text in enumerate(row_data):
                    item = QTableWidgetItem(str(text))
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    if col_idx == 3:
                        item.setForeground(QColor("#EF4444")) # Expenses always RED
                    self.table.setItem(row_idx, col_idx, item)
                    
        elif self.current_tab == "stock":
            self.table.setRowCount(len(self.inventory_records))
            for row_idx, row_data in enumerate(self.inventory_records):
                for col_idx, text in enumerate(row_data):
                    item = QTableWidgetItem(str(text))
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    
                    # Style all key attributes in Blue so it doesn't look like an expense!
                    if col_idx in [0, 2, 3]: # Item Name, Quantity, and Unit
                        item.setForeground(QColor("#3B82F6")) # Clean Inventory Blue
                    elif col_idx == 1: # Size (Added checks to catch verbose database formats)
                        if text == "L" or "Large" in text or text.startswith("L "):
                            item.setForeground(QColor("#60A5FA")) # Medium blue
                        elif text == "XL" or "Extra Large" in text or text.startswith("XL "):
                            item.setForeground(QColor("#A855F7")) # Purple
                        else:
                            item.setForeground(QColor("#94A3B8")) # Gray for "None"
                            
                    self.table.setItem(row_idx, col_idx, item)

    def open_record_expense_modal(self):
        dialog = RecordExpenseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_expense_payload = dialog.get_data()
            
            try:
                api_endpoint = "http://127.0.0.1:8000/api/expenses" 
                response = requests.post(api_endpoint, json=new_expense_payload)
                
                if response.status_code in [200, 201]:
                    # Force fetch both and update immediately
                    self.load_live_database_records()
                    self.load_live_inventory_records()
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

    def open_record_stock_modal(self):
        dialog = RecordStockDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_stock_payload = dialog.get_data()
            
            try:
                api_endpoint = "http://127.0.0.1:8000/api/inventory"
                response = requests.post(api_endpoint, json=new_stock_payload)
                
                if response.status_code in [200, 201]:
                    # Force fetch both and update immediately
                    self.load_live_database_records()
                    self.load_live_inventory_records()
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