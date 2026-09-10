import sys
import os
import json
import urllib.request
import urllib.error
import requests
from datetime import date, datetime, timedelta
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QGraphicsOpacityEffect, QSizePolicy
)
from database import HOLLOWBLOCKS_ITEM_NAME, LOW_STOCK_ALERT_THRESHOLD
from ui_utils import BlurredDialog


# =================================================================
# DETAILED MONTHLY TRANSACTIONS MODAL
# =================================================================
class MonthlyDetailsDialog(BlurredDialog):
    def __init__(self, month_name, transactions, parent=None):
        super().__init__(parent)
        self.month_name = month_name
        self.transactions = transactions
        self.setWindowTitle(f"Detailed Transactions — {self.month_name}")
        self.setMinimumSize(720, 520)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setStyleSheet("""
            QDialog {
                background-color: #0B1120;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 16px;
            }
            QLabel { color: #F8FAFC; }
            QTableWidget {
                background-color: #111827;
                gridline-color: rgba(255,255,255,8);
                color: #E2E8F0;
                border: none;
                border-radius: 10px;
                font-size: 13px;
            }
            QTableWidget::item { padding: 6px 12px; border: none; }
            QTableWidget::item:selected { background-color: rgba(59,130,246,0.15); }
            QHeaderView::section {
                background-color: #0B1120;
                color: #AAB8CA;
                padding: 12px;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,10);
            }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,20); border-radius: 3px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setFixedHeight(3)
        top_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3B82F6, stop:0.5 #8B5CF6, stop:1 #10B981);
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        """)
        layout.addWidget(top_bar)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(28, 24, 28, 24)
        inner_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title_label = QLabel(f"Transactions — {self.month_name}")
        title_label.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #F8FAFC;")
        count_label = QLabel(f"{len(self.transactions)} total record(s)")
        count_label.setStyleSheet("color: #AAB8CA; font-size: 12px;")
        title_col.addWidget(title_label)
        title_col.addWidget(count_label)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(32, 32)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,8);
                color: #94A3B8; border: none;
                border-radius: 8px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(239,68,68,0.2); color: #F87171; }
        """)
        btn_close.clicked.connect(self.reject)

        header_layout.addLayout(title_col)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        inner_layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["DATE", "TYPE", "TRANSACTION DETAILS", "AMOUNT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(self.table.styleSheet() + """
            QTableWidget { alternate-background-color: rgba(255,255,255,3); }
        """)
        self.populate_table()
        inner_layout.addWidget(self.table)
        layout.addWidget(inner)

    def populate_table(self):
        self.table.setRowCount(len(self.transactions))
        self.table.verticalHeader().setDefaultSectionSize(46)

        for row_idx, tx in enumerate(self.transactions):
            date_item = QTableWidgetItem(tx.get("date", "N/A"))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 0, date_item)

            tx_type = str(tx.get("type", "Unknown")).lower()
            type_item = QTableWidgetItem(tx_type.upper())
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, type_item)

            desc_item = QTableWidgetItem(tx.get("description", ""))
            desc_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 2, desc_item)

            amount = float(tx.get("amount", 0.0))
            if tx_type == "inventory":
                amt_str = f"₱{abs(amount):,.2f}"
                amt_item = QTableWidgetItem(amt_str)
                amt_item.setForeground(QColor("#3B82F6"))
                type_item.setForeground(QColor("#3B82F6"))
            elif tx_type == "expense" or amount < 0:
                amt_str = f"−₱{abs(amount):,.2f}"
                amt_item = QTableWidgetItem(amt_str)
                amt_item.setForeground(QColor("#F87171"))
                type_item.setForeground(QColor("#F87171"))
            else:
                amt_str = f"+₱{amount:,.2f}"
                amt_item = QTableWidgetItem(amt_str)
                amt_item.setForeground(QColor("#34D399"))
                type_item.setForeground(QColor("#34D399"))

            amt_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, amt_item)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


# =================================================================
# SINGLE TRANSACTION RECEIPT MODAL
# =================================================================
class ReceiptDialog(BlurredDialog):
    def __init__(self, txn, parent=None):
        super().__init__(parent)
        self.txn = txn or {}
        self.setWindowTitle("Transaction Receipt")
        self.setFixedSize(400, 500)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        tx_type = str(self.txn.get("type", "")).lower()
        try:
            amt = float(self.txn.get("amount", 0) or 0)
        except (TypeError, ValueError):
            amt = 0.0

        if tx_type == "inventory":
            accent = "#3B82F6"
            type_label = "Stock Added"
            sign = ""
        elif tx_type == "expense" or amt < 0:
            accent = "#EF4444"
            type_label = "Expense"
            sign = "−"
        else:
            accent = "#10B981"
            type_label = "Sale"
            sign = "+"

        self.setStyleSheet("""
            QDialog {
                background-color: #0B1120;
                border: 1px solid rgba(255,255,255,20);
                border-radius: 16px;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top_bar = QFrame()
        top_bar.setFixedHeight(4)
        top_bar.setStyleSheet(f"""
            background-color: {accent};
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        """)
        outer.addWidget(top_bar)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(0)

        header_row = QHBoxLayout()
        title = QLabel("Transaction Receipt")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #F1F5F9;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,8);
                color: #94A3B8; border: none;
                border-radius: 8px; font-size: 13px;
            }
            QPushButton:hover { background-color: rgba(239,68,68,0.2); color: #F87171; }
        """)
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)
        layout.addSpacing(14)

        badge = QLabel(type_label.upper())
        badge.setFixedHeight(26)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            background-color: {accent}30;
            color: {accent};
            border: 1px solid {accent};
            border-radius: 13px;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 0 14px;
        """)
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        badge_row = QHBoxLayout()
        badge_row.addWidget(badge)
        badge_row.addStretch()
        layout.addLayout(badge_row)
        layout.addSpacing(22)

        amt_label = QLabel(f"{sign}₱{abs(amt):,.2f}")
        amt_label.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
        amt_label.setStyleSheet(f"color: {accent};")
        amt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(amt_label)

        sub_amt = QLabel("Total Amount")
        sub_amt.setStyleSheet("color: #94A3B8; font-size: 11px;")
        sub_amt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_amt)
        layout.addSpacing(22)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255,255,255,12);")
        layout.addWidget(divider)
        layout.addSpacing(18)

        def detail_row(label_text, value_text):
            row = QHBoxLayout()
            row.setSpacing(12)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
            lbl.setFixedWidth(110)
            val = QLabel(value_text)
            val.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 600;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            val.setWordWrap(True)
            row.addWidget(lbl)
            row.addWidget(val, stretch=1)
            return row

        raw_id = self.txn.get("id")
        details = [
            ("Description", str(self.txn.get("description") or "Transaction")),
            ("Date", str(self.txn.get("date") or "—")),
            ("Transaction ID", f"#{raw_id}" if raw_id is not None else "—"),
        ]
        for label_text, value_text in details:
            layout.addLayout(detail_row(label_text, value_text))
            layout.addSpacing(12)

        layout.addStretch()

        footer_div = QFrame()
        footer_div.setFixedHeight(1)
        footer_div.setStyleSheet("background-color: rgba(255,255,255,10);")
        layout.addWidget(footer_div)
        layout.addSpacing(14)

        footer = QLabel("Magalin Hollow Blocks Trading")
        footer.setStyleSheet("color: #64748B; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        outer.addWidget(inner)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


# =================================================================
# BACKGROUND API FETCH WORKER
# =================================================================
# Dashboard reads from the canonical transaction history.  The inventory
# screen already uses BLOCKFLOW_API_URL with the /api suffix, while the old
# dashboard hardcoded a different URL.  Accept either form so both windows
# always talk to the same backend.
def _dashboard_api_root(api_base_url=None):
    configured = (
        api_base_url
        or os.environ.get("BLOCKFLOW_API_URL", "http://127.0.0.1:8000/api")
    ).rstrip("/")
    return configured[:-4] if configured.endswith("/api") else configured


class DashboardDataWorker(QThread):
    data_loaded = pyqtSignal(dict)

    def __init__(self, api_base_url=None):
        super().__init__()
        self.api_base_url = _dashboard_api_root(api_base_url)

    def run(self):
        result = {
            "current_stock_pcs": 0,
            "stock_by_size": {
                "All Sizes": 0,
                "L": 0,
                "XL": 0,
            },
            "monthly_sales": 0,
            "monthly_expenses": 0,
            "monthly_net_profit": 0,
            "period_totals": {
                "daily": {"sales": 0, "expenses": 0, "net_profit": 0},
                "weekly": {"sales": 0, "expenses": 0, "net_profit": 0},
                "monthly": {"sales": 0, "expenses": 0, "net_profit": 0},
            },
            "low_stock_alerts": [],
            "recent_transactions": [],
            "monthly_history": []
        }

        raw_transactions = []

        # `transactions` is the single source of truth: every successful
        # sales, stock, and expense write creates one row there.  Reading
        # /sales and /history and trying to merge both responses caused sales
        # to be duplicated and made dashboard behavior depend on response
        # shape.
        history_loaded = False
        try:
            req = urllib.request.Request(
                f"{self.api_base_url}/api/history",
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    history_loaded = True
                    raw_res = json.loads(response.read().decode('utf-8'))
                    history_data = raw_res
                    if isinstance(raw_res, dict):
                        history_data = (
                            raw_res.get("history")
                            or raw_res.get("data")
                            or raw_res.get("transactions")
                            or []
                        )
                    if isinstance(history_data, list):
                        for item in history_data:
                            try:
                                amount = float(item.get("amount", 0) or 0)
                            except (TypeError, ValueError):
                                amount = 0.0
                            date_value = (
                                item.get("date")
                                or item.get("date_record")
                                or item.get("date_recorded")
                                or item.get("date_added")
                                or "1970-01-01"
                            )
                            raw_transactions.append({
                                "id": item.get("id"),
                                "type": str(item.get("type", "expense")).lower(),
                                "description": (
                                    item.get("title")
                                    or item.get("description")
                                    or "Transaction"
                                ),
                                "amount": amount,
                                "date": str(date_value),
                                "timestamp": str(date_value),
                            })
        except Exception as e:
            print(f"[API] /api/history offline ({e})")

        # Staff and Admin run as separate desktop processes but share this
        # SQLite database. Prefer that local source when it has data so the
        # dashboard sees a Staff write immediately, even if the API process
        # still has an older database connection or points at another copy.
        # Keep the API response as a fallback for remote deployments.
        try:
            from database import get_transaction_history

            local_history = get_transaction_history()
            if local_history:
                raw_transactions = []
                for item in local_history:
                    try:
                        amount = float(item.get("amount", 0) or 0)
                    except (TypeError, ValueError):
                        amount = 0.0
                    date_value = (
                        item.get("date")
                        or item.get("date_record")
                        or "1970-01-01"
                    )
                    raw_transactions.append({
                        "id": item.get("id"),
                        "type": str(item.get("type", "expense")).lower(),
                        "description": (
                            item.get("title")
                            or item.get("description")
                            or "Transaction"
                        ),
                        "amount": amount,
                        "date": str(date_value),
                        "timestamp": str(date_value),
                    })
        except Exception as e:
            if not history_loaded or not raw_transactions:
                print(f"[DB] Local transaction fallback unavailable ({e})")

        def parse_id(transaction):
            try:
                return int(transaction.get("id") or 0)
            except Exception:
                return 0

        # "Recent" means when the record was saved, not the business date
        # selected in the form.  A Staff member may enter an older sale date,
        # but that record should still appear at the top of Admin's activity.
        raw_transactions.sort(key=parse_id, reverse=True)
        result["recent_transactions"] = raw_transactions

        total_sales = 0
        total_expenses = 0
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        period_totals = {
            "daily": {"sales": 0.0, "expenses": 0.0, "net_profit": 0.0},
            "weekly": {"sales": 0.0, "expenses": 0.0, "net_profit": 0.0},
            "monthly": {"sales": 0.0, "expenses": 0.0, "net_profit": 0.0},
        }
        monthly_map = {}

        for txn in raw_transactions:
            amt = float(txn.get("amount", 0) or 0)
            tx_type = txn["type"].lower()
            is_expense = tx_type == "expense" or (tx_type != "inventory" and amt < 0)

            if is_expense:
                total_expenses += abs(amt)
            elif tx_type == "sale":
                total_sales += amt

            raw_date = str(txn.get("date", "1970-01-01"))
            try:
                month_key = raw_date[:7]
                dt = datetime.strptime(raw_date[:10], "%Y-%m-%d")
                month_label = dt.strftime("%B %Y")

                for period_name, period_start in (
                    ("daily", today),
                    ("weekly", week_start),
                    ("monthly", month_start),
                ):
                    if period_start <= dt.date() <= today:
                        if is_expense:
                            period_totals[period_name]["expenses"] += abs(amt)
                        elif tx_type == "sale":
                            period_totals[period_name]["sales"] += amt
            except Exception:
                month_key = "unknown"
                month_label = "Unknown"

            if month_key not in monthly_map:
                monthly_map[month_key] = {"label": month_label, "sales": 0, "expenses": 0, "tx_count": 0}
            monthly_map[month_key]["tx_count"] += 1
            if is_expense:
                monthly_map[month_key]["expenses"] += abs(amt)
            elif tx_type == "sale":
                monthly_map[month_key]["sales"] += amt

        result["monthly_sales"] = total_sales
        result["monthly_expenses"] = total_expenses
        result["monthly_net_profit"] = total_sales - total_expenses
        for totals in period_totals.values():
            totals["net_profit"] = totals["sales"] - totals["expenses"]
        result["period_totals"] = period_totals

        months_formatted = []
        for key in sorted(monthly_map.keys(), reverse=True):
            stats = monthly_map[key]
            name = stats["label"]
            net = stats["sales"] - stats["expenses"]
            months_formatted.append({
                "month": name,
                "tx_count": f"{stats['tx_count']} txns",
                "sales": f"₱{stats['sales']:,}",
                "expenses": f"₱{stats['expenses']:,}",
                "net": f"₱{net:,}" if net >= 0 else f"−₱{abs(net):,}",
                "net_val": net
            })
        result["monthly_history"] = months_formatted

        inventory_loaded = False
        inventory_data = []
        try:
            req = urllib.request.Request(f"{self.api_base_url}/api/inventory", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    inventory_loaded = True
                    raw_res = json.loads(response.read().decode('utf-8'))
                    inventory_data = raw_res
                    if isinstance(raw_res, dict):
                        inventory_data = raw_res.get("inventory") or raw_res.get("data") or []
        except Exception as e:
            print(f"[API] Inventory offline ({e})")

        try:
            from database import get_all_inventory

            local_inventory = get_all_inventory()
            if local_inventory:
                inventory_data = local_inventory
        except Exception as e:
            if not inventory_loaded or not inventory_data:
                print(f"[DB] Local inventory fallback unavailable ({e})")

        total_stock = 0
        stock_by_size = {"All Sizes": 0, "L": 0, "XL": 0}
        for item in inventory_data:
            try:
                qty = int(item.get("quantity", 0) or 0)
            except (TypeError, ValueError):
                qty = 0
            # The metric is explicitly in pieces.  Include every current pcs
            # record so a newly recorded stock item is reflected even when
            # its name is not exactly "Hollowblocks".
            if str(item.get("unit", "pcs")).strip().lower() != "pcs":
                continue
            total_stock += qty
            stock_by_size["All Sizes"] += qty
            normalized_size = str(item.get("size", "") or "").strip().upper()
            if normalized_size in {"L", "XL"}:
                stock_by_size[normalized_size] += qty
        # Low stock is based on the combined Hollowblocks inventory, not on
        # whichever individual restock record happened to be smallest.
        low_alerts = []
        if inventory_data and total_stock <= LOW_STOCK_ALERT_THRESHOLD:
            low_alerts.append(
                f"{HOLLOWBLOCKS_ITEM_NAME} is running low! ({total_stock:,} pcs left)"
            )
        result["current_stock_pcs"] = total_stock
        result["stock_by_size"] = stock_by_size
        result["low_stock_alerts"] = low_alerts

        self.data_loaded.emit(result)


# =================================================================
# ANALYTICS LOADER WORKER (loads analytics in background)
# =================================================================
class AnalyticsLoaderWorker(QThread):
    """Worker thread to load analytics data without freezing UI."""
    
    loaded = pyqtSignal()  # Signal when ready to create widget
    error = pyqtSignal(str)      # Emits error message if loading fails
    
    def __init__(self, role="owner"):
        super().__init__()
        self.role = role
        self.analytics_data = None
    
    def run(self):
        """Load heavy analytics data in background thread."""
        try:
            # Load transaction history (the heavy operation)
            from analytics_view import _load_transaction_history, _sales_records
            
            print("Loading analytics data in background...")
            history = _load_transaction_history()
            sales = _sales_records(history)
            
            # Store data for main thread to use
            self.analytics_data = {
                'history': history,
                'sales': sales,
                'role': self.role
            }
            
            print("Analytics data loaded successfully!")
            self.loaded.emit()
            
        except Exception as e:
            print(f"Error loading analytics data: {e}")
            self.error.emit(str(e))


# =================================================================
# MAIN DASHBOARD WINDOW  (improved — top nav bar, no sidebar)
# =================================================================
class BlockFlowDashboard(QFrame):
    def __init__(self, role="owner"):
        super().__init__()
        self.setFont(QFont("Segoe UI", 10))
        self.user_role = str(role or "staff").strip().lower()
        self.is_admin = self.user_role in {"owner", "admin"}
        self.setWindowTitle("BlockFlow — Dashboard")
        self.setObjectName("MainWindow")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(current_dir, "image_b08741.png")
        if not os.path.exists(self.image_path):
            self.image_path = os.path.join(current_dir, "image_b08741.jpg")

        self.all_raw_tx_records = []
        self.latest_dashboard_data = {}
        self.metric_filters = {}
        self.metric_titles = {}
        self.metric_subtitles = {}
        self.init_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.load_live_data)
        self.refresh_timer.start()
        self.load_live_data()
        self.setWindowOpacity(0.0)
        self.showFullScreen()
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(500)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

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
            # 5% more transparent than original (195 → 182)
            painter.fillRect(self.rect(), QColor(5, 10, 25, 182))
        painter.end()

    # ── Nav button helper ────────────────────────────────────────────────────
    def _nav_button(self, text, active=False):
        btn = QPushButton(text)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(59,130,246,0.15);
                    color: #93C5FD; border: none;
                    border-radius: 8px; padding: 0 18px;
                    font-size: 13px; font-weight: 700;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #94A3B8;
                    border: none; border-radius: 8px;
                    padding: 0 18px; font-size: 13px; font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,6); color: #CBD5E1;
                }
            """)
        return btn

    # ─────────────────────────────────────────────────────────────────────────
    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ══════════════════════════════════════════════════════════════
        # TOP NAV BAR
        # ══════════════════════════════════════════════════════════════
        nav_bar = QFrame()
        nav_bar.setFixedHeight(68)
        nav_bar.setObjectName("NavBar")
        nav_bar.setStyleSheet("""
            QFrame#NavBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(12, 16, 32, 245), stop:1 rgba(7, 10, 21, 245));
                border-bottom: 1px solid rgba(255,255,255,10);
            }
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(28, 0, 24, 0)
        nav_layout.setSpacing(0)

        brand_frame = QFrame()
        brand_frame.setFixedSize(44, 44)
        brand_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(59,130,246,45), stop:1 rgba(139,92,246,45));
                border: 1px solid rgba(255,255,255,22);
                border-radius: 13px;
            }
        """)
        brand_frame_layout = QVBoxLayout(brand_frame)
        brand_frame_layout.setContentsMargins(0, 0, 0, 0)

        brand_badge = QLabel()
        brand_badge.setFixedSize(30, 30)
        brand_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load Logo.png
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "Logo.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            scaled_logo = logo_pixmap.scaled(
                30, 30,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            brand_badge.setPixmap(scaled_logo)
        else:
            # Fallback if logo not found
            brand_badge.setText("BF")
            brand_badge.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            brand_badge.setStyleSheet("""
                color: white;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #3B82F6, stop:1 #8B5CF6);
                border-radius: 8px;
            """)
        brand_frame_layout.addWidget(brand_badge, 0, Qt.AlignmentFlag.AlignCenter)

        brand_text_col = QVBoxLayout()
        brand_text_col.setSpacing(0)
        brand_label = QLabel("BlockFlow")
        brand_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        brand_label.setStyleSheet("color: #F8FAFC; letter-spacing: 0.3px;")
        brand_sub = QLabel("BLOCKS TRADING")
        brand_sub.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        brand_sub.setStyleSheet("color: #64748B; letter-spacing: 1.4px;")
        brand_text_col.addWidget(brand_label)
        brand_text_col.addWidget(brand_sub)

        nav_layout.addWidget(brand_frame)
        nav_layout.addSpacing(12)
        nav_layout.addLayout(brand_text_col)
        nav_layout.addSpacing(32)

        sep = QFrame()
        sep.setFixedSize(1, 28)
        sep.setStyleSheet("background-color: rgba(255,255,255,10);")
        nav_layout.addWidget(sep)
        nav_layout.addSpacing(28)

        btn_nav_dash = self._nav_button("Dashboard", True)   # active
        btn_nav_inv  = self._nav_button("Inventory", False)
        btn_nav_inv.clicked.connect(self.handle_nav_inventory)

        nav_layout.addWidget(btn_nav_dash)
        nav_layout.addSpacing(4)
        nav_layout.addWidget(btn_nav_inv)
        if self.is_admin:
            btn_nav_analytics = self._nav_button("Analytics", False)
            btn_nav_analytics.clicked.connect(self.handle_nav_analytics)
            nav_layout.addSpacing(4)
            nav_layout.addWidget(btn_nav_analytics)
        nav_layout.addStretch()

        user_chip = QFrame()
        user_chip.setObjectName("UserChip")
        user_chip.setFixedHeight(44)
        user_chip.setStyleSheet("""
            QFrame#UserChip {
                background-color: rgba(30,41,59,150);
                border: 1px solid rgba(255,255,255,14);
                border-radius: 22px;
            }
        """)
        chip_layout = QHBoxLayout(user_chip)
        chip_layout.setContentsMargins(6, 0, 18, 0)
        chip_layout.setSpacing(10)

        avatar_grad = "stop:0 #3B82F6, stop:1 #8B5CF6" if self.is_admin else "stop:0 #14B8A6, stop:1 #0891B2"
        avatar = QLabel("A" if self.is_admin else "S")
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        avatar.setStyleSheet("""
            color: white;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, %s);
            border-radius: 15px;
        """ % avatar_grad)

        role_col = QVBoxLayout()
        role_col.setSpacing(0)
        role_title = QLabel("Admin" if self.is_admin else "Staff")
        role_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        role_title.setStyleSheet("color: #F1F5F9;")
        role_caption = QLabel("Full Access" if self.is_admin else "Limited Access")
        role_caption.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        role_caption.setStyleSheet("color: %s;" % ("#93C5FD" if self.is_admin else "#5EEAD4"))
        role_col.addWidget(role_title)
        role_col.addWidget(role_caption)

        chip_layout.addWidget(avatar)
        chip_layout.addLayout(role_col)

        btn_logout = QPushButton("Logout")
        btn_logout.setFixedHeight(44)
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setStyleSheet("""
            QPushButton {
                color: #F87171;
                background-color: rgba(239,68,68,0.10);
                padding: 0 22px;
                border-radius: 22px;
                border: 1px solid rgba(239,68,68,0.30);
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(239,68,68,0.85);
                border-color: rgba(239,68,68,0.85);
                color: #FEF2F2;
            }
            QPushButton:pressed {
                background-color: rgba(185,28,28,0.95);
            }
        """)
        btn_logout.clicked.connect(self.handle_logout)

        nav_layout.addWidget(user_chip)
        nav_layout.addSpacing(12)
        nav_layout.addWidget(btn_logout)
        root.addWidget(nav_bar)

        accent_line = QFrame()
        accent_line.setFixedHeight(2)
        accent_line.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3B82F6, stop:0.5 #8B5CF6, stop:1 #22D3EE);
        """)
        root.addWidget(accent_line)

        # ══════════════════════════════════════════════════════════════
        # SCROLLABLE WORKSPACE
        # ══════════════════════════════════════════════════════════════
        workspace_container = QScrollArea()
        workspace_container.setWidgetResizable(True)
        workspace_container.setFrameShape(QFrame.Shape.NoFrame)
        workspace_container.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,15); border-radius: 3px; }
        """)

        workspace_widget = QWidget()
        workspace_widget.setObjectName("Workspace")
        workspace_widget.setStyleSheet("""
            QWidget#Workspace { background: transparent; }
            QLabel { background: transparent; border: none; }
        """)

        workspace_layout = QVBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(28, 22, 28, 22)
        workspace_layout.setSpacing(16)

        # ── Page title ────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        header_title = QLabel("Dashboard Overview")
        header_title.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #F8FAFC;")
        sub_title = QLabel("Live business performance — Magalin Hollow Blocks Trading")
        sub_title.setStyleSheet("color: #B8C5D6; font-size: 13px;")
        title_col.addWidget(header_title)
        title_col.addWidget(sub_title)
        title_row.addLayout(title_col)
        title_row.addStretch()
        workspace_layout.addLayout(title_row)

        # ── KPI Cards ─────────────────────────────────────────────────
        # 5% more transparent panels: 210 → 197
        PANEL_BG = "rgba(10, 17, 34, 225)"

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        self.metric_values = {}

        metrics_setup = [
            ("current_stock",     "Current Stock",    "📦",
             "rgba(59,130,246,0.18)",  "#3B82F6", "Finished goods total",
             [("All Sizes", "All Sizes"), ("L (Large)", "L"), ("XL (Extra Large)", "XL")]),
            ("monthly_sales",     "Monthly Sales",    "💰",
             "rgba(16,185,129,0.18)",  "#10B981", "Total revenue this month",
             [("Daily", "daily"), ("Weekly", "weekly"), ("Monthly", "monthly")] if self.is_admin else None),
            ("monthly_expenses",  "Monthly Expenses", "📋",
             "rgba(249,115,22,0.18)",  "#F97316", "Total costs this month",
             [("Daily", "daily"), ("Weekly", "weekly"), ("Monthly", "monthly")] if self.is_admin else None),
        ]
        if self.is_admin:
            metrics_setup.append(
                ("monthly_net_profit", "Net Profit", "📈",
                 "rgba(139,92,246,0.18)", "#8B5CF6", "Sales minus expenses",
                 [("Daily", "daily"), ("Weekly", "weekly"), ("Monthly", "monthly")])
            )

        for i, (key, title, icon, bg, color, sub, filter_options) in enumerate(metrics_setup):
            box = QFrame()
            box.setObjectName("MetricBox")
            box.setStyleSheet(f"""
                QFrame#MetricBox {{
                    background-color: {PANEL_BG};
                    border: 1px solid rgba(255,255,255,9);
                    border-top: 3px solid {color};
                    border-radius: 14px;
                }}
            """)

            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(18, 16, 18, 18)
            box_layout.setSpacing(7)

            icon_row = QHBoxLayout()
            icon_badge = QLabel(icon)
            icon_badge.setFixedSize(38, 38)
            icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_badge.setFont(QFont("Segoe UI", 16))
            icon_badge.setStyleSheet(f"background-color: {bg}; border-radius: 10px;")
            icon_row.addWidget(icon_badge)
            icon_row.addStretch()
            if filter_options is not None:
                filter_box = QComboBox()
                filter_box.setObjectName("MetricFilter")
                filter_box.setFixedHeight(30)
                filter_box.setMinimumWidth(92 if key == "current_stock" else 86)
                filter_box.setStyleSheet("""
                    QComboBox#MetricFilter {
                        background-color: rgba(30, 41, 59, 210);
                        color: #CBD5E1;
                        border: 1px solid rgba(255,255,255,18);
                        border-radius: 8px;
                        padding: 0 8px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                    QComboBox#MetricFilter:hover {
                        border: 1px solid rgba(96,165,250,150);
                        color: #F8FAFC;
                    }
                    QComboBox#MetricFilter::drop-down {
                        border: none;
                        width: 18px;
                    }
                    QComboBox QAbstractItemView {
                        background-color: #111827;
                        color: #E2E8F0;
                        border: 1px solid rgba(255,255,255,18);
                        selection-background-color: #1E3A5F;
                        padding: 4px;
                    }
                """)
                for option_label, option_value in filter_options:
                    filter_box.addItem(option_label, option_value)
                filter_box.setCurrentIndex(len(filter_options) - 1 if key != "current_stock" else 0)
                filter_box.currentIndexChanged.connect(
                    lambda _index, metric_key=key: self.on_metric_filter_changed(metric_key)
                )
                icon_row.addWidget(filter_box)
                self.metric_filters[key] = filter_box
            else:
                # Staff view: period is locked to "Daily" — show a static badge
                # instead of a dropdown, no Weekly/Monthly option available.
                static_badge = QLabel("Daily")
                static_badge.setFixedHeight(30)
                static_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                static_badge.setStyleSheet("""
                    color: #94A3B8;
                    background-color: rgba(30, 41, 59, 140);
                    border: 1px solid rgba(255,255,255,12);
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 600;
                """)
                icon_row.addWidget(static_badge)
                self.metric_filters[key] = None
            box_layout.addLayout(icon_row)

            lbl_title = QLabel(title)
            lbl_title.setStyleSheet(
                "color: #C0CCDA; font-size: 12px; font-weight: 600; letter-spacing: 0.5px;")
            box_layout.addWidget(lbl_title)
            self.metric_titles[key] = lbl_title

            val_lbl = QLabel("—")
            val_lbl.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
            val_lbl.setStyleSheet("color: #F1F5F9;")
            box_layout.addWidget(val_lbl)
            self.metric_values[key] = val_lbl

            lbl_sub = QLabel(sub)
            lbl_sub.setStyleSheet("color: #9EADBF; font-size: 11px;")
            box_layout.addWidget(lbl_sub)
            self.metric_subtitles[key] = lbl_sub

            metrics_grid.addWidget(box, 0, i)

        workspace_layout.addLayout(metrics_grid)

        # ── Transaction History Panel ──────────────────────────────────
        self.history_panel = QFrame()
        self.history_panel.setObjectName("HistoryPanel")
        self.history_panel.setStyleSheet(f"""
            QFrame#HistoryPanel {{
                background-color: {PANEL_BG};
                border: 1px solid rgba(255,255,255,9);
                border-radius: 14px;
            }}
        """)
        self.history_layout = QVBoxLayout(self.history_panel)
        self.history_layout.setContentsMargins(18, 16, 18, 18)
        self.history_layout.setSpacing(10)

        header_bar = QHBoxLayout()
        left_header = QVBoxLayout()
        left_header.setSpacing(3)
        title_text = QLabel("Transaction History")
        title_text.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_text.setStyleSheet("color: #F1F5F9;")
        sub_desc_text = QLabel("Monthly summaries — click a card to view details")
        sub_desc_text.setStyleSheet("color: #AAB8CA; font-size: 11px;")
        left_header.addWidget(title_text)
        left_header.addWidget(sub_desc_text)

        self.calendar_toggle_btn = QPushButton("View Calendar")
        self.calendar_toggle_btn.setFixedHeight(36)
        self.calendar_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(139,92,246,0.15);
                color: #A78BFA;
                border: 1px solid rgba(139,92,246,0.3);
                border-radius: 10px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(139,92,246,0.25);
                color: #C4B5FD;
            }
        """)
        self.calendar_toggle_btn.clicked.connect(self.toggle_history_calendar)

        header_bar.addLayout(left_header)
        header_bar.addStretch()
        header_bar.addWidget(self.calendar_toggle_btn)
        self.history_layout.addLayout(header_bar)

        self.monthly_grid_widget = QWidget()
        self.monthly_grid_widget.setVisible(False)
        self.monthly_grid_layout = QGridLayout(self.monthly_grid_widget)
        self.monthly_grid_layout.setSpacing(14)
        self.monthly_grid_layout.setContentsMargins(0, 8, 0, 0)
        self.history_layout.addWidget(self.monthly_grid_widget)
        workspace_layout.addWidget(self.history_panel)
        # Staff only get the "Recent Transactions" list below — the full
        # monthly Transaction History summary/calendar is admin-only.
        self.history_panel.setVisible(self.is_admin)

        # ── Bottom panels ─────────────────────────────────────────────
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        # Stock Alerts
        self.left_panel = QFrame()
        self.left_panel.setObjectName("LeftPanel")
        self.left_panel.setStyleSheet(f"""
            QFrame#LeftPanel {{
                background-color: {PANEL_BG};
                border: 1px solid rgba(255,255,255,9);
                border-radius: 14px;
            }}
        """)
        self.left_panel_layout = QVBoxLayout(self.left_panel)
        self.left_panel_layout.setContentsMargins(18, 16, 18, 18)
        self.left_panel_layout.setSpacing(10)

        left_header_row = QHBoxLayout()
        left_header_col = QVBoxLayout()
        left_header_col.setSpacing(3)
        left_title = QLabel("Stock Alerts")
        left_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        left_title.setStyleSheet("color: #F1F5F9;")
        left_sub = QLabel("Items below threshold")
        left_sub.setStyleSheet("color: #AAB8CA; font-size: 11px;")
        left_header_col.addWidget(left_title)
        left_header_col.addWidget(left_sub)
        left_header_row.addLayout(left_header_col)
        left_header_row.addStretch()
        self.left_panel_layout.addLayout(left_header_row)

        self.alerts_container = QVBoxLayout()
        self.alerts_container.setSpacing(8)
        self.left_panel_layout.addLayout(self.alerts_container)
        self.left_panel_layout.addStretch()

        # Recent Transactions
        self.right_panel = QFrame()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setStyleSheet(f"""
            QFrame#RightPanel {{
                background-color: {PANEL_BG};
                border: 1px solid rgba(255,255,255,9);
                border-radius: 14px;
            }}
        """)
        self.right_panel_layout = QVBoxLayout(self.right_panel)
        self.right_panel_layout.setContentsMargins(18, 16, 18, 18)
        self.right_panel_layout.setSpacing(10)

        right_header_col = QVBoxLayout()
        right_header_col.setSpacing(3)
        right_title = QLabel("Recent Transactions")
        right_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        right_title.setStyleSheet("color: #F1F5F9;")
        right_sub = QLabel("Latest 5 activity records")
        right_sub.setStyleSheet("color: #AAB8CA; font-size: 11px;")
        right_header_col.addWidget(right_title)
        right_header_col.addWidget(right_sub)
        self.right_panel_layout.addLayout(right_header_col)

        self.transactions_container = QVBoxLayout()
        self.transactions_container.setSpacing(8)
        self.right_panel_layout.addLayout(self.transactions_container)
        self.right_panel_layout.addStretch()

        bottom_layout.addWidget(self.left_panel, stretch=4)
        bottom_layout.addWidget(self.right_panel, stretch=5)
        workspace_layout.addLayout(bottom_layout, stretch=1)

        workspace_container.setWidget(workspace_widget)
        root.addWidget(workspace_container)

    # ─────────────────────────────────────────────────────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        # The timer keeps an already-open admin dashboard current.  A show
        # event can happen while switching windows, so don't start a second
        # request when the existing worker is still loading.
        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def load_live_data(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            return
        self.worker = DashboardDataWorker()
        self.worker.data_loaded.connect(self.on_data_received)
        self.worker.start()

    def on_data_received(self, data):
        self.all_raw_tx_records = data.get("recent_transactions", [])
        self.latest_dashboard_data = data
        self.update_metric_cards()

        # Stock alerts
        while self.alerts_container.count():
            item = self.alerts_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data["low_stock_alerts"]:
            ok_frame = QFrame()
            ok_frame.setStyleSheet("""
                background-color: rgba(16,185,129,0.08);
                border: 1px solid rgba(16,185,129,0.2);
                border-left: 3px solid #10B981;
                border-radius: 10px;
            """)
            ok_layout = QHBoxLayout(ok_frame)
            ok_layout.setContentsMargins(16, 12, 16, 12)
            ok_text = QLabel("All stock levels are healthy")
            ok_text.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            ok_text.setStyleSheet("color: #34D399; border: none; background: transparent;")
            ok_layout.addWidget(ok_text)
            self.alerts_container.addWidget(ok_frame)
        else:
            for alert in data["low_stock_alerts"]:
                alert_frame = QFrame()
                alert_frame.setStyleSheet("""
                    background-color: rgba(239,68,68,0.08);
                    border: 1px solid rgba(239,68,68,0.2);
                    border-left: 3px solid #EF4444;
                    border-radius: 10px;
                """)
                al = QHBoxLayout(alert_frame)
                al.setContentsMargins(14, 10, 14, 10)
                al_text = QLabel(f"Low Stock: {alert}")
                al_text.setStyleSheet(
                    "color: #F87171; font-size: 13px; font-weight: 600; "
                    "border: none; background: transparent;")
                al.addWidget(al_text)
                self.alerts_container.addWidget(alert_frame)

        # Recent transactions
        while self.transactions_container.count():
            item = self.transactions_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data["recent_transactions"]:
            no_lbl = QLabel("No transactions found yet.")
            no_lbl.setStyleSheet("color: #AAB8CA; font-size: 13px; padding: 8px 0;")
            self.transactions_container.addWidget(no_lbl)
        else:
            for txn in data["recent_transactions"][:5]:
                tx_type = txn.get("type", "").lower()
                amt = float(txn.get("amount", 0))

                if tx_type == "inventory":
                    color = "#3B82F6"
                    bg    = "rgba(59,130,246,0.10)"
                    border = "#3B82F6"
                    prefix = ""
                elif tx_type == "expense" or amt < 0:
                    color  = "#F87171"
                    bg     = "rgba(239,68,68,0.08)"
                    border = "#EF4444"
                    prefix = "−"
                else:
                    color  = "#34D399"
                    bg     = "rgba(16,185,129,0.08)"
                    border = "#10B981"
                    prefix = "+"

                tx_frame = QFrame()
                tx_frame.setStyleSheet(f"""
                    background-color: {bg};
                    border: 1px solid rgba(255,255,255,6);
                    border-left: 3px solid {border};
                    border-radius: 10px;
                """)
                tx_row = QHBoxLayout(tx_frame)
                tx_row.setContentsMargins(14, 10, 14, 10)

                desc_col = QVBoxLayout()
                desc_col.setSpacing(2)
                desc_lbl = QLabel(txn.get("description", "Transaction"))
                desc_lbl.setStyleSheet(
                    "color: #CBD5E1; font-size: 13px; font-weight: 600; "
                    "border: none; background: transparent;")
                date_lbl = QLabel(txn.get("date", ""))
                date_lbl.setStyleSheet(
                    "color: #9EADBF; font-size: 11px; border: none; background: transparent;")
                desc_col.addWidget(desc_lbl)
                desc_col.addWidget(date_lbl)

                amt_lbl = QLabel(f"{prefix}₱{abs(amt):,.0f}")
                amt_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
                amt_lbl.setStyleSheet(
                    f"color: {color}; border: none; background: transparent;")
                amt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                tx_row.addLayout(desc_col)
                tx_row.addStretch()
                tx_row.addWidget(amt_lbl)
                tx_frame.setCursor(Qt.CursorShape.PointingHandCursor)
                tx_frame.mousePressEvent = lambda e, t=dict(txn): self.show_receipt(t)
                self.transactions_container.addWidget(tx_frame)

    def show_receipt(self, txn):
        dialog = ReceiptDialog(txn, self)
        dialog.exec()

    def on_metric_filter_changed(self, metric_key):
        if self.latest_dashboard_data:
            self.update_metric_cards()

    def update_metric_cards(self):
        data = self.latest_dashboard_data
        if not data:
            return

        stock_filter = self.metric_filters["current_stock"].currentData()
        stock_by_size = data.get("stock_by_size", {})
        stock = int(stock_by_size.get(stock_filter, data.get("current_stock_pcs", 0)) or 0)
        self.metric_values["current_stock"].setText(f"{stock:,} pcs")
        self.metric_titles["current_stock"].setText("Current Stock")
        self.metric_subtitles["current_stock"].setText(
            "Finished goods total" if stock_filter == "All Sizes"
            else f"{self.metric_filters['current_stock'].currentText()} blocks"
        )

        period_totals = data.get("period_totals", {})
        period_labels = {
            "daily": "today",
            "weekly": "this week",
            "monthly": "this month",
        }
        metric_config = (
            ("monthly_sales", "sales", "Sales", "#10B981"),
            ("monthly_expenses", "expenses", "Expenses", "#F97316"),
            ("monthly_net_profit", "net_profit", "Net Profit", "#8B5CF6"),
        )
        for metric_key, value_key, title, color in metric_config:
            if metric_key not in self.metric_filters:
                continue
            filter_widget = self.metric_filters[metric_key]
            if filter_widget is not None:
                period_key = filter_widget.currentData() or "monthly"
                period_prefix = filter_widget.currentText()
            else:
                period_key = "daily"
                period_prefix = "Daily"
            totals = period_totals.get(period_key, {})
            value = float(totals.get(value_key, 0) or 0)
            self.metric_titles[metric_key].setText(
                f"{period_prefix} {title}"
            )
            self.metric_subtitles[metric_key].setText(
                f"{'Sales minus expenses' if value_key == 'net_profit' else ('Total revenue' if value_key == 'sales' else 'Total costs')} {period_labels.get(period_key, 'this month')}"
            )
            value_label = self.metric_values[metric_key]
            value_label.setText(
                f"₱{value:,.0f}" if value >= 0 else f"−₱{abs(value):,.0f}"
            )
            value_label.setStyleSheet(
                f"color: {'#34D399' if value >= 0 else '#F87171'}; "
                "font-size: 24px; font-weight: bold;"
            )

        # Monthly history calendar
        while self.monthly_grid_layout.count():
            item = self.monthly_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, month_data in enumerate(data["monthly_history"]):
            card = QFrame()
            net_val = month_data["net_val"]
            card_color = "#34D399" if net_val >= 0 else "#F87171"
            card_bg    = "rgba(16,185,129,0.08)" if net_val >= 0 else "rgba(239,68,68,0.08)"
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {card_bg};
                    border: 1px solid rgba(255,255,255,8);
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    background-color: rgba(255,255,255,0.07);
                    border: 1px solid rgba(255,255,255,18);
                    cursor: pointer;
                }}
            """)
            card.setCursor(Qt.CursorShape.PointingHandCursor)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(6)

            month_lbl = QLabel(month_data["month"])
            month_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            month_lbl.setStyleSheet("color: #F1F5F9;")

            txn_lbl = QLabel(month_data["tx_count"])
            txn_lbl.setStyleSheet("color: #9EADBF; font-size: 11px;")

            row2 = QHBoxLayout()
            sales_lbl = QLabel(f"↑ {month_data['sales']}")
            sales_lbl.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")
            exp_lbl = QLabel(f"↓ {month_data['expenses']}")
            exp_lbl.setStyleSheet("color: #F87171; font-size: 12px; font-weight: 600;")
            row2.addWidget(sales_lbl)
            row2.addStretch()
            row2.addWidget(exp_lbl)

            net_lbl_card = QLabel(f"Net: {month_data['net']}")
            net_lbl_card.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            net_lbl_card.setStyleSheet(f"color: {card_color};")

            card_layout.addWidget(month_lbl)
            card_layout.addWidget(txn_lbl)
            card_layout.addLayout(row2)
            card_layout.addWidget(net_lbl_card)

            month_key = month_data["month"]
            card.mousePressEvent = lambda e, mk=month_key: self.on_monthly_card_clicked(mk)

            col = idx % 4
            row = idx // 4
            self.monthly_grid_layout.addWidget(card, row, col)

    def on_monthly_card_clicked(self, month_label):
        try:
            dt = datetime.strptime(month_label, "%B %Y")
            target_prefix = dt.strftime("%Y-%m")
        except Exception:
            target_prefix = "2026-07"

        monthly_filtered = [
            tx for tx in self.all_raw_tx_records
            if tx.get("date", "").startswith(target_prefix)
        ]
        dialog = MonthlyDetailsDialog(month_label, monthly_filtered, self)
        dialog.exec()

    def toggle_history_calendar(self):
        is_visible = self.monthly_grid_widget.isVisible()
        self.monthly_grid_widget.setVisible(not is_visible)
        self.calendar_toggle_btn.setText(
            "Hide Calendar" if not is_visible else "View Calendar")

    def handle_nav_inventory(self):
        try:
            from inventory_view import BlockFlowInventory
            self.inv_window = BlockFlowInventory(role=self.user_role)
            self.inv_window.show()
            self.close()
        except ImportError:
            pass

    def handle_nav_analytics(self):
        if not self.is_admin:
            return
        try:
            from loading_screen import LoadingScreen
            
            # Show loading screen
            self.analytics_loading = LoadingScreen(self, "Loading Analytics Data...")
            self.analytics_loading.show()
            
            # Start background data loader for analytics
            self.analytics_loader = AnalyticsLoaderWorker(role=self.user_role)
            self.analytics_loader.loaded.connect(self._on_analytics_data_loaded)
            self.analytics_loader.error.connect(self._on_analytics_error)
            self.analytics_loader.start()
        except ImportError as e:
            print(f"Error loading analytics: {e}")
    
    def _on_analytics_data_loaded(self):
        """Called when analytics data finishes loading in background."""
        try:
            from analytics_view import BlockFlowAnalytics
            
            print("Creating analytics window in main thread...")
            # Create analytics window in MAIN THREAD (thread-safe)
            self.analytics_window = BlockFlowAnalytics(role=self.user_role)
            self.analytics_window.show()
            
            # Close the current dashboard
            self.close()
            
            # Close loading screen
            if hasattr(self, 'analytics_loading'):
                self.analytics_loading.close()
                
            print("Analytics window displayed!")
        except Exception as e:
            print(f"Error showing analytics: {e}")
            if hasattr(self, 'analytics_loading'):
                self.analytics_loading.close()
    
    def _on_analytics_error(self, error_msg):
        """Called if analytics loading fails."""
        print(f"Analytics loading error: {error_msg}")
        if hasattr(self, 'analytics_loading'):
            self.analytics_loading.close()

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
