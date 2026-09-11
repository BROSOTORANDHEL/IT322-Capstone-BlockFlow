"""Shared UI helpers for BlockFlow.

BlurredDialog is the base every popup in the app uses instead of QDialog:
  - the window behind it softly blurs while it's open
  - the dialog itself eases in (fades + rises slightly) instead of popping
    open instantly, and eases back out the same way on close

Everything else about QDialog works exactly the same, so existing
subclasses only need to change their base class.
"""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QEventLoop, QParallelAnimationGroup, QPoint, QPropertyAnimation
from PyQt6.QtWidgets import QDialog, QGraphicsBlurEffect, QMessageBox, QWidget


def _background_target(dialog: QDialog) -> QWidget | None:
    """The top-level window sitting behind this dialog, if any."""
    parent = dialog.parentWidget()
    if parent is None:
        return None
    return parent.window()


def apply_background_blur(dialog: QDialog, radius: float = 16.0) -> QGraphicsBlurEffect | None:
    """Attach a blur effect (starting at 0) to the window behind ``dialog``."""
    target = _background_target(dialog)
    if target is None:
        return None
    effect = QGraphicsBlurEffect(target)
    effect.setBlurRadius(0.0)
    target.setGraphicsEffect(effect)
    return effect


def clear_background_blur(dialog: QDialog) -> None:
    """Remove any blur previously applied behind ``dialog``."""
    target = _background_target(dialog)
    if target is None:
        return
    target.setGraphicsEffect(None)


class BlurredDialog(QDialog):
    """A QDialog that blurs the window behind it and animates in/out.

    Subclass this instead of QDialog for any popup that should ease into
    view (and blur/dim the app behind it) rather than just appearing.
    """

    ENTER_MS = 220
    EXIT_MS = 150
    BLUR_RADIUS = 16.0
    RISE_PX = 18  # how far the dialog rises into place as it fades in

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._entered = False
        self._exited = False
        self._blur_effect: QGraphicsBlurEffect | None = None
        self._enter_anim: QParallelAnimationGroup | None = None

    def showEvent(self, event):
        super().showEvent(event)
        if self._entered:
            return
        self._entered = True

        self._blur_effect = apply_background_blur(self, self.BLUR_RADIUS)

        # Animate position + opacity only (never size), so nothing inside
        # the dialog — charts included — has to reflow mid-animation.
        end_pos = self.pos()
        start_pos = end_pos + QPoint(0, self.RISE_PX)

        self.setWindowOpacity(0.0)
        self.move(start_pos)

        opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        opacity_anim.setDuration(self.ENTER_MS)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        pos_anim = QPropertyAnimation(self, b"pos", self)
        pos_anim.setDuration(self.ENTER_MS)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(end_pos)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity_anim)
        group.addAnimation(pos_anim)

        if self._blur_effect is not None:
            blur_anim = QPropertyAnimation(self._blur_effect, b"blurRadius", self)
            blur_anim.setDuration(self.ENTER_MS)
            blur_anim.setStartValue(0.0)
            blur_anim.setEndValue(self.BLUR_RADIUS)
            blur_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(blur_anim)

        self._enter_anim = group
        group.start()

    def done(self, result):
        # QDialog routes accept()/reject()/the window's close button/Escape
        # all through here, so this is the single place we need to animate
        # the exit and clear the blur before the dialog actually closes.
        self._play_exit_animation()
        clear_background_blur(self)
        super().done(result)

    def _play_exit_animation(self):
        if self._exited or not self._entered:
            return
        self._exited = True

        loop = QEventLoop(self)
        group = QParallelAnimationGroup(self)

        opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        opacity_anim.setDuration(self.EXIT_MS)
        opacity_anim.setStartValue(self.windowOpacity())
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(opacity_anim)

        pos_anim = QPropertyAnimation(self, b"pos", self)
        pos_anim.setDuration(self.EXIT_MS)
        pos_anim.setStartValue(self.pos())
        pos_anim.setEndValue(self.pos() + QPoint(0, self.RISE_PX))
        pos_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(pos_anim)

        if self._blur_effect is not None:
            blur_anim = QPropertyAnimation(self._blur_effect, b"blurRadius", self)
            blur_anim.setDuration(self.EXIT_MS)
            blur_anim.setStartValue(self._blur_effect.blurRadius())
            blur_anim.setEndValue(0.0)
            blur_anim.setEasingCurve(QEasingCurve.Type.InCubic)
            group.addAnimation(blur_anim)

        group.finished.connect(loop.quit)
        group.start()
        loop.exec()


# ─────────────────────────────────────────────────────────────────────────────
# Themed message boxes
#
# The stock QMessageBox.warning/critical/information dialogs pick up almost
# no styling from the app's dark theme on some systems, which can leave the
# text (or the OK button) nearly invisible against a black background. These
# helpers build a QMessageBox by hand and force a dark, readable style
# directly onto that instance, so they always render correctly regardless of
# OS theme. Use them exactly like the QMessageBox static methods they replace:
# show_warning(self, "Title", "Message"), etc.
# ─────────────────────────────────────────────────────────────────────────────

_MESSAGE_BOX_STYLE = """
    QMessageBox {
        background-color: #0F172A;
    }
    QMessageBox QLabel {
        color: #F1F5F9;
        font-size: 16px;
        background: transparent;
    }
    QMessageBox QPushButton {
        background-color: #4F46E5;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        min-width: 72px;
        font-weight: 600;
        font-size: 15px;
    }
    QMessageBox QPushButton:hover {
        background-color: #6366F1;
    }
    QMessageBox QPushButton:pressed {
        background-color: #4338CA;
    }
"""


def _show_message(parent, icon: QMessageBox.Icon, title: str, text: str) -> int:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStyleSheet(_MESSAGE_BOX_STYLE)
    return box.exec()


def show_warning(parent, title: str, text: str) -> int:
    return _show_message(parent, QMessageBox.Icon.Warning, title, text)


def show_critical(parent, title: str, text: str) -> int:
    return _show_message(parent, QMessageBox.Icon.Critical, title, text)


def show_information(parent, title: str, text: str) -> int:
    return _show_message(parent, QMessageBox.Icon.Information, title, text)
