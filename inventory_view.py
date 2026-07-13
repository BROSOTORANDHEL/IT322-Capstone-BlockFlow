import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)

class BlockFlowInventory(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlockFlow - Inventory Management")
        self.init_ui()
        self.showFullScreen()

    def init_ui(self):
        # Base window background styling matching the dark blue layout
        self.setStyleSheet("background-color: #0F172A;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -----------------------------------------------------------------
        # 1. SIDEBAR NAVIGATION
        # -----------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #1E293B; border-right: 1px solid #334155;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 40)
        sidebar_layout.setSpacing(15)

        # App Title Logo
        logo_label = QLabel("BlockFlow")
        logo_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        logo_label.setStyleSheet("color: #F8FAFC;")
        sidebar_layout.addWidget(logo_label)

        sub_logo = QLabel("Magalin Trading")
        sub_logo.setFont(QFont("Arial", 10))
        sub_logo.setStyleSheet("color: #94A3B8; margin-bottom: 20px;")
        sidebar_layout.addWidget(sub_logo)

        # Nav Links
        btn_dash = QPushButton("  Dashboard")
        btn_inv = QPushButton("  Inventory")
        btn_analytics = QPushButton("  Analytics")

        # Style side navigation items (highlighting Inventory since we are on it)
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

        # -----------------------------------------------------------------
        # 2. MAIN OPERATION CONTAINER VIEW
        # -----------------------------------------------------------------
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(25)

        # Header Bar Layout (Title + User Info + Logout)
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

        # Action Cards Section (Horizontal)
        cards_layout = QHBoxLayout()
        
        card_expense = self.create_action_card("Record Expenses", "Raw materials, maintenance, other", "#EF4444")
        card_stock = self.create_action_card("Record Stock", "Add new stock to inventory", "#3B82F6")
        card_sales = self.create_action_card("Record Sales", "Daily sales transactions", "#10B981")
        
        cards_layout.addWidget(card_expense)
        cards_layout.addWidget(card_stock)
        cards_layout.addWidget(card_sales)
        content_layout.addLayout(cards_layout)

        # Table Subtitle + Add Expense Action Button
        table_header_layout = QHBoxLayout()
        table_title = QLabel("Expense Records")
        table_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        table_title.setStyleSheet("color: #F8FAFC;")
        
        btn_add_expense = QPushButton("+ Add Expense")
        btn_add_expense.setStyleSheet("background-color: #EF4444; color: white; padding: 8px 16px; font-weight: bold; border-radius: 6px;")
        
        table_header_layout.addWidget(table_title)
        table_header_layout.addStretch()
        table_header_layout.addWidget(btn_add_expense)
        content_layout.addLayout(table_header_layout)

        # 📊 INVENTORY DATA TABLE DATASET
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
        
        # Format layout columns evenly
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Populate Mock Data matching user layout view
        mock_data = [
            ("2026-01-08", "Raw Material", "Portland Cement (50 bags)", "-₱12,500"),
            ("2026-01-20", "Maintenance", "Mixer Repair", "-₱2,500"),
            ("2026-02-10", "Raw Material", "Screened Sand (10 cubic meters)", "-₱8,000")
        ]
        
        self.table.setRowCount(len(mock_data))
        for row_idx, row_data in enumerate(mock_data):
            for col_idx, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                # Highlight negative pricing amounts cleanly
                if col_idx == 3:
                    item.setForeground(QColor("#EF4444"))
                self.table.setItem(row_idx, col_idx, item)

        content_layout.addWidget(self.table)

        # Compile Main Window Segments
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area)

    def create_action_card(self, title, description, border_color):
        card = QFrame()
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

    def handle_logout(self):
        from login_view import BlockFlowLogin
        self.login_window = BlockFlowLogin()
        self.login_window.show()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BlockFlowInventory()
    window.show()
    sys.exit(app.exec())