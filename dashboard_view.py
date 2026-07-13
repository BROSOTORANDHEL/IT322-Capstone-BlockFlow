import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QFrame, QGridLayout
)

class BlockFlowDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlockFlow - Dashboard Overview")
        
        # Dark premium slate background color
        self.setStyleSheet("background-color: #0F172A;")
        self.showFullScreen()
        self.init_ui()

    def init_ui(self):
        # Master horizontal layout splitting Sidebar (Left) and Main Workspace (Right)
        master_layout = QHBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)

        # ==========================================
        # 🔲 SIDEBAR PANEL (LEFT)
        # ==========================================
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #1E293B; 
                border-right: 1px solid rgba(255, 255, 255, 15);
            }
            QLabel { color: #F8FAFC; }
            QPushButton {
                background-color: transparent; color: #94A3B8;
                border: none; border-radius: 8px;
                padding: 12px; font-size: 14px; text-align: left;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 20); color: #F8FAFC; }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(15)

        # Brand / Title Headings
        brand_label = QLabel("BlockFlow")
        brand_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        sidebar_layout.addWidget(brand_label)
        
        sub_brand = QLabel("Magalin Trading")
        sub_brand.setStyleSheet("color: #64748B; font-size: 12px;")
        sidebar_layout.addWidget(sub_brand)
        sidebar_layout.addSpacing(30)

        # Navigation Options
        sidebar_layout.addWidget(QPushButton("⬜ Dashboard"))
        sidebar_layout.addWidget(QPushButton("📦 Inventory"))
        sidebar_layout.addWidget(QPushButton("📈 Analytics"))
        
        sidebar_layout.addStretch() # Pushes logout cleanly to the bottom row

        # 🚪 Logout Button Configuration
        logout_btn = QPushButton("🚪 Logout")
        logout_btn.setStyleSheet("color: #EF4444;")
        # 🚀 REDIRECTION TRIGGER TO THE LOGIN VIEW
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)

        master_layout.addWidget(sidebar)

        # ==========================================
        # 🖼️ MAIN WORKSPACE (RIGHT)
        # ==========================================
        workspace_widget = QWidget()
        workspace_layout = QVBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(40, 30, 40, 30)
        workspace_layout.setSpacing(25)

        # --- Top Header Info Area ---
        header_layout = QHBoxLayout()
        
        title_block = QVBoxLayout()
        header_title = QLabel("Dashboard Overview")
        header_title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #F8FAFC;")
        sub_title = QLabel("Track your business performance")
        sub_title.setStyleSheet("color: #64748B; font-size: 13px;")
        title_block.addWidget(header_title)
        title_block.addWidget(sub_title)
        
        header_right_mock = QLabel("👤 Admin Profile")
        header_right_mock.setStyleSheet("color: #F8FAFC; background-color: #1E293B; padding: 10px; border-radius: 8px;")
        
        header_layout.addLayout(title_block)
        header_layout.addStretch()
        header_layout.addWidget(header_right_mock)
        workspace_layout.addLayout(header_layout)

        # --- 4 Overview Metric Boxes Layout (Grid Row) ---
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(20)

        metric_styles = """
            QFrame {
                background-color: rgba(30, 41, 59, 200);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 14px;
            }
            QLabel { color: white; font-size: 14px; }
        """

        for i in range(4):
            box = QFrame()
            box.setStyleSheet(metric_styles)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(25, 25, 25, 25)
            box_layout.setSpacing(8)
            
            lbl_title = QLabel(f"Metric Title {i+1}")
            lbl_title.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
            
            lbl_value = QLabel("₱0" if i > 0 else "12,700")
            lbl_value.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            
            lbl_sub = QLabel("Placeholder status text details")
            lbl_sub.setStyleSheet("color: #64748B; font-size: 11px;")
            
            box_layout.addWidget(lbl_title)
            box_layout.addWidget(lbl_value)
            box_layout.addWidget(lbl_sub)
            
            metrics_grid.addWidget(box, 0, i)

        workspace_layout.addLayout(metrics_grid)

        # --- Bottom Split Section Containers ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(25)

        # Left Bottom Container Block (Low Stock Alerts)
        left_panel = QFrame()
        left_panel.setStyleSheet(metric_styles)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(20, 20, 20, 20)
        
        left_title = QLabel("Low Stock Alerts")
        left_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        left_panel_layout.addWidget(left_title)
        left_panel_layout.addStretch()
        
        # Right Bottom Container Block (Recent Transactions)
        right_panel = QFrame()
        right_panel.setStyleSheet(metric_styles)
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(20, 20, 20, 20)
        
        right_title = QLabel("Recent Transactions")
        right_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        right_panel_layout.addWidget(right_title)
        right_panel_layout.addStretch()

        bottom_layout.addWidget(left_panel, stretch=4)  
        bottom_layout.addWidget(right_panel, stretch=4)

        workspace_layout.addLayout(bottom_layout, stretch=1)
        master_layout.addWidget(workspace_widget)

    # 🚪 ACTION: Handles dynamic route destruction back to login panel
    def handle_logout(self):
        try:
            from login_view import BlockFlowLogin
            self.login_window = BlockFlowLogin()
            self.login_window.show()
            self.close()  # Closes the dashboard window safely without killing the application
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