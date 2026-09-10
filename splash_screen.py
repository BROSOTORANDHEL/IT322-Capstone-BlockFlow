"""Welcome splash screen for BlockFlow after login."""

import os
import sys
import math
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication


class SplashScreen(QWidget):
    """Beautiful welcome splash screen with animated dots and rotating logo."""
    
    # Signal emitted when splash screen is closed
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()
        
        # Load background image
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(script_dir, "image_b08741.png")
        if not os.path.exists(self.image_path):
            self.image_path = os.path.join(script_dir, "image_b08741.jpg")
        
        # Load logo
        logo_path = os.path.join(script_dir, "Logo.png")
        self.logo_pixmap = QPixmap(logo_path)
        
        # Animation variables
        self.spinner_angle = 0
        self.dot_count = 0
        self.dot_cycle = 0
        self.alpha = 0.0
        
        # Setup layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Logo label
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(self.logo_label)
        layout.addSpacing(30)
        
        # Title
        self.title_label = QLabel("Welcome to BlockFlow")
        self.title_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #F8FAFC;")
        layout.addWidget(self.title_label)
        layout.addSpacing(10)
        
        # Subtitle
        self.subtitle_label = QLabel("Your Business Management System")
        self.subtitle_label.setFont(QFont("Segoe UI", 14))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #CBD5E1;")
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(40)
        
        # Loading dots
        self.dots_label = QLabel()
        self.dots_label.setFont(QFont("Segoe UI", 16))
        self.dots_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dots_label.setStyleSheet("color: #3B82F6;")
        layout.addWidget(self.dots_label)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Start animations
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)  # Slower update rate for smoother animation
        
        # Fade in animation
        self.setWindowOpacity(0.0)
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(500)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
        
        # Auto close after 5 seconds
        QTimer.singleShot(5000, self.close_splash)
    
    def animate(self):
        """Animate logo pulse and loading dots."""
        # Gentle pulse effect instead of rotation
        self.spinner_angle = (self.spinner_angle + 1) % 360
        self.update_logo()
        
        # Smooth dot animation - change every 3 frames
        self.dot_cycle = (self.dot_cycle + 1) % 12
        if self.dot_cycle < 3:
            self.dot_count = 1
        elif self.dot_cycle < 6:
            self.dot_count = 2
        elif self.dot_cycle < 9:
            self.dot_count = 3
        else:
            self.dot_count = 2
        
        dots = "●" * self.dot_count + "○" * (3 - self.dot_count)
        self.dots_label.setText(dots)
    
    def update_logo(self):
        """Update logo with gentle pulse effect."""
        if not self.logo_pixmap.isNull():
            # Create gentle pulse scale effect (between 0.95 and 1.05)
            pulse = 0.975 + 0.05 * math.sin(self.spinner_angle * math.pi / 180)
            size = int(100 * pulse)
            
            scaled = self.logo_pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the scaled logo in a 100x100 canvas
            canvas = QPixmap(100, 100)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            x = (100 - size) // 2
            y = (100 - size) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            
            self.logo_label.setPixmap(canvas)
    
    def close_splash(self):
        """Close splash screen with fade out effect."""
        self.timer.stop()
        
        # Fade out
        fade_anim = QPropertyAnimation(self, b"windowOpacity")
        fade_anim.setDuration(300)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        fade_anim.finished.connect(self.on_close_finished)
        fade_anim.start()
        self._fade_anim = fade_anim  # Keep reference
    
    def on_close_finished(self):
        """Called when fade out animation finishes."""
        self.close()
        self.closed.emit()  # Emit signal so login knows splash is closed
    
    def paintEvent(self, event):
        """Paint background image."""
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
        super().paintEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    sys.exit(app.exec())
