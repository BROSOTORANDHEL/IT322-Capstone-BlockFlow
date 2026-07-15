import sys
import os
import json
import urllib.request
import urllib.error
import requests  # Clean fallback or API access
from datetime import datetime
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QFrame, QGridLayout, QScrollArea,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView
)

# =================================================================
# 🔎 DETAILED MONTHLY TRANSACTIONS MODAL
# =================================================================
class MonthlyDetailsDialog(QDialog):
    """
    Sleek overlay popup displaying a clear table of all individual 
    sales, stock inputs, and expenses for the selected month.
    """
    def __init__(self, month_name, transactions, parent=None):
        super().__init__(parent)
        self.month_name = month_name
        self.transactions = transactions
        self.setWindowTitle(f"Detailed Transactions - {self.month_name}")
        self.setMinimumSize(700, 500)
        self.init_ui()

    def init_ui(self):
        # Frameless, modern styling that blends with the dark glass dashboard
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                border: 2px solid #334155;
                border-radius: 12px;
            }
            QLabel {
                color: #F8FAFC;
            }
            QTableWidget {
                background-color: #1E293B;
                gridline-color: #334155;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 10px;
                font-weight: bold;
                border-bottom: 2px solid #334155;
                border-top: none;
                border-left: none;
                border-right: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(15)

        # Header layout with Title and X button
        header_layout = QHBoxLayout()
        title_label = QLabel(f"Transactions for {self.month_name}")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                color: #94A3B8; 
                border: none; 
                font-size: 16px; 
                font-weight: bold;
            }
            QPushButton:hover { color: #EF4444; }
        """)
        btn_close.clicked.connect(self.reject)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        layout.addLayout(header_layout)

        # Summary Metrics Row inside Modal
        summary_label = QLabel(f"Showing {len(self.transactions)} total record(s)")
        summary_label.setStyleSheet("color: #64748B; font-size: 12px; font-style: italic;")
        layout.addWidget(summary_label)

        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["DATE", "TYPE", "TRANSACTION DETAILS", "AMOUNT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.populate_table()
        layout.addWidget(self.table)

    def populate_table(self):
        self.table.setRowCount(len(self.transactions))
        
        for row_idx, tx in enumerate(self.transactions):
            # 1. Date column
            date_item = QTableWidgetItem(tx.get("date", "N/A"))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, date_item)
            
            # 2. Type Column
            tx_type = str(tx.get("type", "Unknown")).upper()
            type_item = QTableWidgetItem(tx_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 1, type_item)
            
            # 3. Description Column
            desc_item = QTableWidgetItem(tx.get("description", "Unspecified Detail"))
            self.table.setItem(row_idx, 2, desc_item)
            
            # 4. Colored amount column based on expense vs income
            amount = float(tx.get("amount", 0.0))
            is_expense = tx.get("type", "").lower() in ["expense", "inventory"] or amount < 0
            
            if is_expense:
                amt_str = f"-₱{abs(amount):,.2f}"
                amt_item = QTableWidgetItem(amt_str)
                amt_item.setForeground(QColor("#EF4444"))  # Vivid Red
            else:
                amt_str = f"+₱{amount:,.2f}"
                amt_item = QTableWidgetItem(amt_str)
                amt_item.setForeground(QColor("#10B981"))  # Emerald Green
                
            amt_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, amt_item)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


# =================================================================
# 🌐 API FETCH WORKER (Safely Sandboxed to Prevent UI Crashes)
# =================================================================
class DashboardDataWorker(QThread):
    """
    Background worker that fetches from BOTH /api/history and /api/sales,
    merges them chronologically, and calculates live dashboard statistics.
    """
    data_loaded = pyqtSignal(dict)

    def __init__(self, api_base_url="http://127.0.0.1:8000"):
        super().__init__()
        self.api_base_url = api_base_url

    def run(self):
        result = {
            "current_stock_pcs": 0,
            "monthly_sales": 0,
            "monthly_expenses": 0,
            "monthly_net_profit": 0,
            "low_stock_alerts": [],
            "recent_transactions": [],
            "monthly_history": []
        }

        raw_transactions = []

        # 1. Fetch sales logs safely from /api/sales
        try:
            req = urllib.request.Request(f"{self.api_base_url}/api/sales", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    raw_res = json.loads(response.read().decode('utf-8'))
                    sales_data = raw_res
                    if isinstance(raw_res, dict):
                        sales_data = raw_res.get("sales") or raw_res.get("data") or raw_res.get("history") or []
                    
                    if isinstance(sales_data, list):
                        for sale in sales_data:
                            qty = float(sale.get("quantity", 0))
                            block_str = sale.get("block_size", "")
                            
                            price = 7.0
                            if "7" in block_str:
                                price = 7.0
                            elif "6" in block_str:
                                price = 6.0
                            elif "5" in block_str:
                                price = 5.0

                            amount = sale.get("amount") or (qty * price)
                            
                            raw_transactions.append({
                                "type": "sale",
                                "description": f"{sale.get('customer_name', 'Walk-in')} - {int(qty)} pcs ({sale.get('block_size', 'Blocks')})",
                                "amount": amount,
                                "date": sale.get("sale_date", "2026-07-02"),
                                "timestamp": sale.get("sale_date", "2026-07-02")
                            })
        except Exception as e:
            print(f"[API Log] Safe bypass: /api/sales offline or unreadable ({e})")

        # 2. Fetch general transaction logs safely from /api/history
        try:
            req = urllib.request.Request(f"{self.api_base_url}/api/history", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    raw_res = json.loads(response.read().decode('utf-8'))
                    history_data = raw_res
                    if isinstance(raw_res, dict):
                        history_data = raw_res.get("history") or raw_res.get("data") or []
                        
                    if isinstance(history_data, list):
                        for item in history_data:
                            db_title = item.get("title") or item.get("description") or "Generic Transaction"
                            
                            if item.get("type", "").lower() == "sale" and any(tx["description"] == db_title for tx in raw_transactions):
                                continue
                            
                            raw_transactions.append({
                                "type": item.get("type", "expense"),
                                "description": db_title,
                                "amount": float(item.get("amount", 0)),
                                "date": item.get("date", "2026-07-02"),
                                "timestamp": item.get("date", "2026-07-02")
                            })
        except Exception as e:
            print(f"[API Log] Safe bypass: /api/history offline or unreadable ({e})")

        # 3. Sort merged list chronologically
        def parse_date(date_str):
            try:
                return datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception:
                return datetime.min

        raw_transactions.sort(key=lambda x: parse_date(x["date"]), reverse=True)
        result["recent_transactions"] = raw_transactions

        # 4. Process calculations dynamically
        total_sales = 0
        total_expenses = 0
        monthly_map = {}

        for txn in raw_transactions:
            amt = txn["amount"]
            is_expense = txn["type"].lower() == "expense" or amt < 0
            
            if is_expense:
                total_expenses += abs(amt)
            else:
                total_sales += amt

            raw_date = txn["date"]
            year_month = raw_date[:7] if len(raw_date) >= 7 else "2026-07"
            
            if year_month not in monthly_map:
                monthly_map[year_month] = {"sales": 0, "expenses": 0, "tx_count": 0}
            
            monthly_map[year_month]["tx_count"] += 1
            if is_expense:
                monthly_map[year_month]["expenses"] += abs(amt)
            else:
                monthly_map[year_month]["sales"] += amt

        result["monthly_sales"] = total_sales
        result["monthly_expenses"] = total_expenses
        result["monthly_net_profit"] = total_sales - total_expenses

        # 5. Format monthly map for display
        months_formatted = []
        month_names = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November", "12": "December"
        }
        for ym, stats in sorted(monthly_map.items(), reverse=True):
            parts = ym.split("-")
            name = f"{month_names.get(parts[1], parts[1])} {parts[0]}" if len(parts) == 2 else ym
            net = stats["sales"] - stats["expenses"]
            
            months_formatted.append({
                "month": name,
                "tx_count": f"{stats['tx_count']} txns",
                "sales": f"₱{stats['sales']:,}",
                "expenses": f"₱{stats['expenses']:,}",
                "net": f"₱{net:,}" if net >= 0 else f"-₱{abs(net):,}",
                "net_val": net
            })
        result["monthly_history"] = months_formatted

        # 6. Fetch inventory safely
        try:
            req = urllib.request.Request(f"{self.api_base_url}/api/inventory", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    raw_res = json.loads(response.read().decode('utf-8'))
                    inventory_data = raw_res
                    if isinstance(raw_res, dict):
                        inventory_data = raw_res.get("inventory") or raw_res.get("data") or []
                    
                    total_stock = 0
                    low_alerts = []
                    for item in inventory_data:
                        qty = int(item.get("quantity", 0))
                        total_stock += qty
                        threshold = int(item.get("low_stock_threshold", 100))
                        if qty <= threshold:
                            low_alerts.append(f"{item.get('name', 'Product')} is running low! ({qty} left)")
                    result["current_stock_pcs"] = total_stock
                    result["low_stock_alerts"] = low_alerts
        except Exception as e:
            print(f"[API Log] Safe bypass: Inventory status offline ({e})")

        self.data_loaded.emit(result)


# =================================================================
# 🖼️ MAIN VIEW PORT
# =================================================================
class BlockFlowDashboard(QFrame):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlockFlow - Dashboard Overview")
        self.setObjectName("MainWindow")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(current_dir, "image_b08741.png")
        clean_image_path = image_path.replace("\\", "/")
        
        self.setStyleSheet(f"""
            QFrame#MainWindow {{
                border-image: url("{clean_image_path}") 0 0 0 0 stretch stretch;
            }}
        """)
        
        # Store full raw transaction lists locally for filtering dialog launches
        self.all_raw_tx_records = []
        
        self.init_ui()
        self.load_live_data()
        self.showFullScreen()

    def init_ui(self):
        master_layout = QHBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)

        # 🔲 SIDEBAR PANEL (LEFT)
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 41, 59, 0.90);
                border-right: 1px solid rgba(51, 65, 85, 0.3);
            }
            QLabel { color: #F8FAFC; border: none; background: transparent; }
            QPushButton {
                background-color: transparent; color: #94A3B8;
                border: none; border-radius: 8px;
                padding: 12px 16px; font-size: 14px; text-align: left;
                font-weight: 500;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); color: #F8FAFC; }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 40)
        sidebar_layout.setSpacing(12)

        brand_label = QLabel("BlockFlow")
        brand_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        sidebar_layout.addWidget(brand_label)
        
        sub_brand = QLabel("Magalin Trading")
        sub_brand.setStyleSheet("color: #64748B; font-size: 12px; margin-bottom: 25px; border: none; background: transparent;")
        sidebar_layout.addWidget(sub_brand)

        btn_dash = QPushButton("📊  Dashboard")
        btn_dash.setStyleSheet("""
            QPushButton {
                background-color: rgba(51, 65, 85, 0.6); color: #F8FAFC;
                border-left: 4px solid #3B82F6; border-radius: 4px;
                font-weight: bold; padding-left: 12px;
            }
        """)
        btn_inv = QPushButton("📦  Inventory")
        btn_analytics = QPushButton("📈  Analytics")
        
        sidebar_layout.addWidget(btn_dash)
        sidebar_layout.addWidget(btn_inv)
        sidebar_layout.addWidget(btn_analytics)
        sidebar_layout.addStretch()

        logout_btn = QPushButton("🚪  Logout")
        logout_btn.setStyleSheet("""
            QPushButton { color: #EF4444; font-weight: bold; border: none; }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.15); color: #F87171; }
        """)
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)

        master_layout.addWidget(sidebar)

        # 🖼️ MAIN WORKSPACE (RIGHT)
        workspace_container = QScrollArea()
        workspace_container.setWidgetResizable(True)
        workspace_container.setFrameShape(QFrame.Shape.NoFrame)
        workspace_container.setStyleSheet("background: transparent;")

        workspace_widget = QWidget()
        workspace_widget.setObjectName("Workspace")
        workspace_widget.setStyleSheet("""
            QWidget#Workspace {
                background-color: rgba(15, 23, 42, 0.82);
            }
            QLabel { background: transparent; border: none; }
        """)
        
        workspace_layout = QVBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(40, 30, 40, 30)
        workspace_layout.setSpacing(25)

        # Row 1: Workspace Top Navigation & Profile Bar
        top_nav_layout = QHBoxLayout()
        
        title_block = QVBoxLayout()
        header_title = QLabel("Dashboard Overview")
        header_title.setFont(QFont("Arial", 26, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #F8FAFC; border: none;")
        sub_title = QLabel("Track your business performance")
        sub_title.setStyleSheet("color: #94A3B8; font-size: 13px; border: none;")
        title_block.addWidget(header_title)
        title_block.addWidget(sub_title)
        
        top_nav_layout.addLayout(title_block)
        top_nav_layout.addStretch()
        
        profile_container = QFrame()
        profile_container.setStyleSheet("background: transparent; border: none;")
        profile_layout = QHBoxLayout(profile_container)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(10)
        
        admin_badge = QLabel("A  Admin")
        admin_badge.setStyleSheet("""
            color: #F8FAFC; background-color: rgba(30, 41, 59, 0.8); 
            padding: 8px 16px; border-radius: 18px; 
            border: 1px solid rgba(255, 255, 255, 0.1); font-weight: 500;
        """)
        
        top_logout_btn = QPushButton("↪ Logout")
        top_logout_btn.setStyleSheet("""
            QPushButton {
                color: #F8FAFC; background-color: rgba(30, 41, 59, 0.8); 
                padding: 8px 16px; border-radius: 18px; 
                border: 1px solid rgba(255, 255, 255, 0.1); font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.4);
            }
        """)
        top_logout_btn.clicked.connect(self.handle_logout)
        
        profile_layout.addWidget(admin_badge)
        profile_layout.addWidget(top_logout_btn)
        top_nav_layout.addWidget(profile_container)
        
        workspace_layout.addLayout(top_nav_layout)

        # Row 2: KPI Metrics Cards
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(20)

        self.metric_values = {}
        
        metrics_setup = [
            ("current_stock", "Current Stock", "📦", "rgba(59, 130, 246, 0.2)", "#3B82F6", "Finished goods total", "All ∨"),
            ("monthly_sales", "Monthly Sales", "📈", "rgba(16, 185, 129, 0.2)", "#10B981", "Goal Progress <span style='color:#10B981;'>100%</span>", "monthly ∨"),
            ("monthly_expenses", "Monthly Expenses", "⚡", "rgba(249, 115, 22, 0.2)", "#F97316", "Total monthly costs", "monthly ∨"),
            ("monthly_net_profit", "Monthly Net Profit", "₱", "rgba(139, 92, 246, 0.2)", "#8B5CF6", "Sales minus expenses", "monthly ∨"),
        ]

        for i, (key, title, icon, bg, color, sub, flt) in enumerate(metrics_setup):
            box = QFrame()
            box.setObjectName("MetricBox")
            box.setStyleSheet("""
                QFrame#MetricBox {
                    background-color: rgba(30, 41, 59, 0.65);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                }
            """)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(20, 20, 20, 20)
            box_layout.setSpacing(12)
            
            card_header = QHBoxLayout()
            icon_lbl = QLabel(icon)
            icon_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            icon_lbl.setFixedSize(36, 36)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet(f"background-color: {bg}; color: {color}; border-radius: 8px;")
            
            filter_btn = QPushButton(flt)
            filter_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #64748B; font-size: 11px;
                    border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 4px 8px;
                }
            """)
            card_header.addWidget(icon_lbl)
            card_header.addStretch()
            card_header.addWidget(filter_btn)
            box_layout.addLayout(card_header)
            
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("color: #94A3B8; font-size: 13px;")
            box_layout.addWidget(lbl_title)

            val_lbl = QLabel("0")
            val_lbl.setFont(QFont("Arial", 22, QFont.Weight.Bold))
            val_lbl.setStyleSheet("color: #F8FAFC;")
            box_layout.addWidget(val_lbl)
            self.metric_values[key] = val_lbl
            
            lbl_sub = QLabel(sub)
            lbl_sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
            box_layout.addWidget(lbl_sub)
            
            metrics_grid.addWidget(box, 0, i)

        workspace_layout.addLayout(metrics_grid)

        # 📅 TRANSACTION HISTORY PANEL (COLLAPSIBLE CALENDAR)
        self.history_panel = QFrame()
        self.history_panel.setObjectName("HistoryPanel")
        self.history_panel.setStyleSheet("""
            QFrame#HistoryPanel {
                background-color: rgba(30, 41, 59, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        self.history_layout = QVBoxLayout(self.history_panel)
        self.history_layout.setContentsMargins(20, 20, 20, 20)
        self.history_layout.setSpacing(15)

        header_bar_layout = QHBoxLayout()
        icon_frame = QLabel("📅")
        icon_frame.setFont(QFont("Arial", 14))
        icon_frame.setFixedSize(36, 36)
        icon_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_frame.setStyleSheet("background-color: rgba(139, 92, 246, 0.2); color: #8B5CF6; border-radius: 8px;")
        
        text_label_layout = QVBoxLayout()
        text_label_layout.setSpacing(2)
        title_text = QLabel("Transaction History")
        title_text.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title_text.setStyleSheet("color: #F8FAFC;")
        sub_desc_text = QLabel("View monthly summaries")
        sub_desc_text.setStyleSheet("color: #64748B; font-size: 11px;")
        text_label_layout.addWidget(title_text)
        text_label_layout.addWidget(sub_desc_text)

        self.calendar_toggle_btn = QPushButton("View Calendar")
        self.calendar_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 10px 18px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        self.calendar_toggle_btn.clicked.connect(self.toggle_history_calendar)

        header_bar_layout.addWidget(icon_frame)
        header_bar_layout.addSpacing(10)
        header_bar_layout.addLayout(text_label_layout)
        header_bar_layout.addStretch()
        header_bar_layout.addWidget(self.calendar_toggle_btn)
        self.history_layout.addLayout(header_bar_layout)

        # Calendar body panel
        self.monthly_grid_widget = QWidget()
        self.monthly_grid_widget.setVisible(False)
        self.monthly_grid_layout = QGridLayout(self.monthly_grid_widget)
        self.monthly_grid_layout.setSpacing(15)
        self.monthly_grid_layout.setContentsMargins(0, 10, 0, 0)
        
        self.history_layout.addWidget(self.monthly_grid_widget)
        workspace_layout.addWidget(self.history_panel)

        # 📊 BOTTOM SPLIT PANELS
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(25)

        # --- LEFT PANEL: Low Stock Alerts ---
        self.left_panel = QFrame()
        self.left_panel.setObjectName("LeftPanel")
        self.left_panel.setStyleSheet("""
            QFrame#LeftPanel {
                background-color: rgba(30, 41, 59, 0.65); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px;
            }
        """)
        self.left_panel_layout = QVBoxLayout(self.left_panel)
        self.left_panel_layout.setContentsMargins(24, 24, 24, 24)
        self.left_panel_layout.setSpacing(15)
        
        left_title_layout = QHBoxLayout()
        left_title = QLabel("Low Stock Alerts")
        left_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        left_title.setStyleSheet("color: #F8FAFC;")
        left_title_layout.addWidget(left_title)
        left_title_layout.addStretch()
        self.left_panel_layout.addLayout(left_title_layout)

        self.alerts_container = QVBoxLayout()
        self.left_panel_layout.addLayout(self.alerts_container)
        self.left_panel_layout.addStretch()
        
        # --- RIGHT PANEL: Recent Transactions ---
        self.right_panel = QFrame()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setStyleSheet("""
            QFrame#RightPanel {
                background-color: rgba(30, 41, 59, 0.65); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px;
            }
        """)
        self.right_panel_layout = QVBoxLayout(self.right_panel)
        self.right_panel_layout.setContentsMargins(24, 24, 24, 24)
        self.right_panel_layout.setSpacing(15)
        
        right_title_layout = QHBoxLayout()
        right_title = QLabel("Recent Transactions")
        right_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        right_title.setStyleSheet("color: #F8FAFC;")
        right_title_layout.addWidget(right_title)
        right_title_layout.addStretch()
        self.right_panel_layout.addLayout(right_title_layout)

        self.transactions_container = QVBoxLayout()
        self.right_panel_layout.addLayout(self.transactions_container)
        self.right_panel_layout.addStretch()

        bottom_layout.addWidget(self.left_panel, stretch=4)  
        bottom_layout.addWidget(self.right_panel, stretch=5)

        workspace_layout.addLayout(bottom_layout, stretch=1)
        workspace_container.setWidget(workspace_widget)
        master_layout.addWidget(workspace_container)

    # =================================================================
    # ⚙️ LIVE DATA LOADING LOGIC (ASYNC CONNECTION)
    # =================================================================
    def showEvent(self, event):
        super().showEvent(event)
        self.load_live_data()

    def load_live_data(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            
        self.worker = DashboardDataWorker()
        self.worker.data_loaded.connect(self.on_data_received)
        self.worker.start()

    def on_data_received(self, data):
        # Cache raw chronologically ordered transactions safely
        self.all_raw_tx_records = data.get("recent_transactions", [])
        
        # 1. Update Main KPI metrics values
        self.metric_values["current_stock"].setText(f"{data['current_stock_pcs']:,}<span style='font-size: 14px; font-weight: normal; color: #64748B;'> pcs</span>")
        self.metric_values["monthly_sales"].setText(f"₱{data['monthly_sales']:,}")
        self.metric_values["monthly_expenses"].setText(f"₱{data['monthly_expenses']:,}")
        self.metric_values["monthly_net_profit"].setText(f"₱{data['monthly_net_profit']:,}")

        # 2. Update Low Stock Alerts
        while self.alerts_container.count():
            item = self.alerts_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data["low_stock_alerts"]:
            healthy_banner = QFrame()
            healthy_banner.setStyleSheet("background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px;")
            banner_layout = QHBoxLayout(healthy_banner)
            banner_text = QLabel("✓  All stock levels are healthy")
            banner_text.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            banner_text.setStyleSheet("color: #10B981;")
            banner_layout.addWidget(banner_text, alignment=Qt.AlignmentFlag.AlignCenter)
            self.alerts_container.addWidget(healthy_banner)
        else:
            for alert in data["low_stock_alerts"]:
                alert_lbl = QLabel(f"⚠️ {alert}")
                alert_lbl.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: bold; background: rgba(239, 68, 68, 0.1); padding: 8px; border-radius: 6px;")
                self.alerts_container.addWidget(alert_lbl)

        # 3. Update Recent Transactions
        while self.transactions_container.count():
            item = self.transactions_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data["recent_transactions"]:
            no_tx_lbl = QLabel("No transactions found yet.")
            no_tx_lbl.setStyleSheet("color: #64748B; font-size: 13px; padding: 10px;")
            self.transactions_container.addWidget(no_tx_lbl)
        else:
            for txn in data["recent_transactions"][:5]:  # Display up to 5 latest items
                row_strip = QFrame()
                row_strip.setStyleSheet("background-color: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 10px;")
                row_layout = QHBoxLayout(row_strip)
                row_layout.setContentsMargins(15, 12, 15, 12)

                is_expense = txn.get("type", "").lower() == "expense" or float(txn.get("amount", 0)) < 0
                amt = float(txn.get("amount", 0))

                prefix = "-" if is_expense else "+"
                color = "#EF4444" if is_expense else "#10B981"
                icon = "⚡" if is_expense else "📈"
                bg = "rgba(239, 68, 68, 0.15)" if is_expense else "rgba(16, 185, 129, 0.15)"

                tx_icon = QLabel(icon)
                tx_icon.setFixedSize(32, 32)
                tx_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                tx_icon.setStyleSheet(f"background-color: {bg}; color: {color}; border-radius: 16px; font-weight: bold;")
                
                details_layout = QVBoxLayout()
                
                tx_name = QLabel(txn.get("description", "Transaction Log"))
                tx_name.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 13px;")
                
                tx_date = QLabel(txn.get("date", "Today"))
                tx_date.setStyleSheet("color: #64748B; font-size: 11px;")
                
                details_layout.addWidget(tx_name)
                details_layout.addWidget(tx_date)

                tx_val = QLabel(f"{prefix}₱{abs(amt):,}")
                tx_val.setFont(QFont("Arial", 13, QFont.Weight.Bold))
                tx_val.setStyleSheet(f"color: {color};")

                row_layout.addWidget(tx_icon)
                row_layout.addSpacing(10)
                row_layout.addLayout(details_layout)
                row_layout.addStretch()
                row_layout.addWidget(tx_val)
                self.transactions_container.addWidget(row_strip)

        # 4. Populate calendar dynamically with real month groupings
        self.populate_calendar(data["monthly_history"])

    # =================================================================
    # 📆 DYNAMIC CALENDAR GENERATION & SELECTION EVENT HANDLERS
    # =================================================================
    def populate_calendar(self, monthly_history):
        while self.monthly_grid_layout.count():
            item = self.monthly_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not monthly_history:
            empty_msg = QLabel("No monthly data calculated. Log transactions to construct summaries.")
            empty_msg.setStyleSheet("color: #64748B; font-size: 13px; padding: 20px;")
            self.monthly_grid_layout.addWidget(empty_msg, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            return

        for index, item in enumerate(monthly_history):
            month_card = QFrame()
            month_card.setObjectName("MonthCard")
            
            # Interactive hover animations and click layouts
            month_card.setStyleSheet("""
                QFrame#MonthCard {
                    background-color: rgba(15, 23, 42, 0.5); 
                    border: 1px solid rgba(255, 255, 255, 0.08); 
                    border-radius: 10px;
                }
                QFrame#MonthCard:hover {
                    background-color: rgba(15, 23, 42, 0.85); 
                    border-color: #8B5CF6;
                }
            """)
            
            # Change mouse cursor to hand pointer to indicate clickability
            month_card.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Override card click mousePressEvent
            month_card.mousePressEvent = lambda event, m_name=item["month"]: self.show_monthly_details(m_name)

            card_v_layout = QVBoxLayout(month_card)
            card_v_layout.setContentsMargins(15, 15, 15, 15)
            card_v_layout.setSpacing(10)

            card_header_layout = QHBoxLayout()
            m_title = QLabel(item["month"])
            m_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            m_title.setStyleSheet("color: #F8FAFC;")
            
            badge = QLabel(item["tx_count"])
            badge.setStyleSheet("color: #94A3B8; background-color: rgba(255, 255, 255, 0.06); border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: bold;")
            card_header_layout.addWidget(m_title)
            card_header_layout.addStretch()
            card_header_layout.addWidget(badge)
            card_v_layout.addLayout(card_header_layout)

            details_layout = QVBoxLayout()
            details_layout.setSpacing(6)

            for label, value, color in [("Sales:", item["sales"], "#10B981"), ("Expenses:", item["expenses"], "#EF4444")]:
                row = QHBoxLayout()
                row.addWidget(QLabel(label, styleSheet="color: #94A3B8; font-size: 12px;"))
                row.addStretch()
                val_lbl = QLabel(value, styleSheet=f"color: {color}; font-weight: bold; font-size: 12px;")
                row.addWidget(val_lbl)
                details_layout.addLayout(row)

            div = QFrame()
            div.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
            details_layout.addWidget(div)

            net_row = QHBoxLayout()
            net_row.addWidget(QLabel("Net:", styleSheet="color: #94A3B8; font-size: 12px;"))
            net_row.addStretch()
            
            net_color = "#10B981" if item["net_val"] >= 0 else "#EF4444"
            net_row.addWidget(QLabel(item["net"], styleSheet=f"color: {net_color}; font-weight: bold; font-size: 12px;"))
            details_layout.addLayout(net_row)
            
            card_v_layout.addLayout(details_layout)
            self.monthly_grid_layout.addWidget(month_card, index // 3, index % 3)

    def show_monthly_details(self, target_month_label):
        """Filters all transactions for the selected month card and brings up details Dialog."""
        month_mappings = {
            "January": "01", "February": "02", "March": "03", "April": "04",
            "May": "05", "June": "06", "July": "07", "August": "08",
            "September": "09", "October": "10", "November": "11", "December": "12"
        }

        try:
            parts = target_month_label.split()
            month_name = parts[0]
            year_val = parts[1]
            month_num = month_mappings.get(month_name, "01")
            target_prefix = f"{year_val}-{month_num}"  # e.g., "2026-07"
        except Exception:
            target_prefix = "2026-07"

        # Dynamically filter cached list matching year-month prefix
        monthly_filtered = []
        for tx in self.all_raw_tx_records:
            tx_date = tx.get("date", "")
            if tx_date and tx_date.startswith(target_prefix):
                monthly_filtered.append(tx)

        # Launch modern Dialog modal
        dialog = MonthlyDetailsDialog(target_month_label, monthly_filtered, self)
        dialog.exec()

    def toggle_history_calendar(self):
        is_visible = self.monthly_grid_widget.isVisible()
        self.monthly_grid_widget.setVisible(not is_visible)
        self.calendar_toggle_btn.setText("Hide Calendar" if not is_visible else "View Calendar")

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
    window = BlockFlowDashboard()
    window.show()
    sys.exit(app.exec())