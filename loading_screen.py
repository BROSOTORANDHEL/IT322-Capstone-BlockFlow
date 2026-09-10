"""Loading screen dialog for BlockFlow with animated spinner."""

import os
import sys
import math
from PyQt6.QtCore import Qt, QTimer, QSize, QRect
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QFrame
)

from ui_utils import BlurredDialog


class LoadingScreen(BlurredDialog):
    """Animated loading screen with BlockFlow logo and spinner."""
    
    def __init__(self, parent=None, title="Loading"):
        super().__init__(parent)
        self.title_text = title
        self.spinner_angle = 0
        
        # Setup window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 300)
        self.setStyleSheet("background-color: transparent;")
        
        # Center on parent or screen
        if parent:
            parent_pos = parent.pos()
            self.move(
                parent_pos.x() + (parent.width() - self.width()) // 2,
                parent_pos.y() + (parent.height() - self.height()) // 2
            )
        
        # Load logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "Logo.png")
        self.logo_pixmap = QPixmap(logo_path)
        
        # Setup layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create background frame
        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(8, 13, 26, 240);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 15);
            }
        """)
        
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(20, 40, 20, 40)
        bg_layout.setSpacing(20)
        
        # Logo label
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_logo()
        bg_layout.addWidget(self.logo_label)
        
        # Loading text
        self.loading_text = QLabel(self.title_text)
        self.loading_text.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_text.setStyleSheet("color: #F8FAFC;")
        bg_layout.addWidget(self.loading_text)
        
        # Subtext
        self.subtext = QLabel("Please wait...")
        self.subtext.setFont(QFont("Segoe UI", 11))
        self.subtext.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtext.setStyleSheet("color: #64748B;")
        bg_layout.addWidget(self.subtext)
        
        bg_layout.addStretch()
        layout.addWidget(self.bg_frame)
        
        # Animation timer for spinner
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_spinner)
        self.timer.start(100)  # Slower update rate for smoother animation
        
        self.setModal(True)
    
    def update_logo(self):
        """Update logo with gentle pulse effect."""
        if not self.logo_pixmap.isNull():
            # Create gentle pulse scale effect (between 0.95 and 1.05)
            pulse = 0.975 + 0.05 * math.sin(self.spinner_angle * math.pi / 180)
            size = int(80 * pulse)
            
            # Scale logo
            scaled = self.logo_pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the scaled logo in an 80x80 canvas
            canvas = QPixmap(80, 80)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            x = (80 - size) // 2
            y = (80 - size) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            
            self.logo_label.setPixmap(canvas)
    
    def animate_spinner(self):
        """Animate the spinner with gentle pulse."""
        self.spinner_angle = (self.spinner_angle + 1) % 360
        self.update_logo()
    
    def closeEvent(self, event):
        """Stop timer when closing."""
        self.timer.stop()
        super().closeEvent(event)
    
    def paintEvent(self, event):
        """Paint semi-transparent background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw semi-transparent overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        
        # Draw frame background with styling
        painter.fillRect(self.rect(), QColor(8, 13, 26, 240))
        
        painter.end()
        super().paintEvent(event)


if __name__ == "__main__":
    app = __import__("PyQt6.QtWidgets", fromlist=["QApplication"]).QApplication(sys.argv)
    loading = LoadingScreen(title="Loading Analytics...")
    loading.show()
    sys.exit(app.exec())
