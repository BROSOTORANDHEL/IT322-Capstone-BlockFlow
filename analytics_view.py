"""Compact sales analytics screen for BlockFlow."""

from __future__ import annotations

import csv
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import requests
from statsmodels.tsa.ar_model import AutoReg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QDialog,
    QGridLayout,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from database import get_transaction_history


API_BASE_URL = os.environ.get(
    "BLOCKFLOW_API_URL",
    "http://127.0.0.1:8000/api",
).rstrip("/")


# ============================================================
# COLORS
# ============================================================

BLUE = "#3B82F6"
BLUE_DARK = "#2563EB"

# Match the darker Inventory interface
PANEL = "rgba(7, 13, 27, 238)"
PANEL_INNER = "rgba(10, 17, 32, 235)"

TEXT = "#F8FAFC"
TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#CBD5E1"
MUTED = "#AEBBCB"
MUTED_DARK = "#94A3B8"

GREEN = "#10B981"
GREEN_LIGHT = "#A7F3D0"
GREEN_TEXT = "#D1FAE5"


# ============================================================
# DATE / SALES HELPERS
# ============================================================

def _parse_date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _sales_records(
    records: list[dict[str, Any]]
) -> list[tuple[date, float]]:
    sales = []

    for record in records:
        if str(record.get("type", "")).lower() != "sale":
            continue

        recorded_date = _parse_date(record.get("date"))

        if recorded_date is None:
            continue

        try:
            amount = float(record.get("amount", 0) or 0)
        except (TypeError, ValueError):
            continue

        sales.append((recorded_date, amount))

    return sales


def _load_transaction_history() -> list[dict[str, Any]]:
    """Load the same transaction source as the Dashboard.

    The API is preferred so Analytics and Dashboard always reflect the same
    data when the desktop client and API process use separate working
    directories. The existing local SQLite read remains a safe offline
    fallback and preserves standalone usage.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/history",
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
    except (requests.RequestException, ValueError, TypeError):
        pass

    return get_transaction_history()


def _shift_month(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset

    return date(
        index // 12,
        index % 12 + 1,
        1,
    )


def _series_for_period(
    sales: list[tuple[date, float]],
    period: str,
) -> list[dict[str, Any]]:

    today = date.today()

    # --------------------------------------------------------
    # WEEKLY
    # --------------------------------------------------------

    if period == "weekly":

        current_week = today - timedelta(
            days=today.weekday()
        )

        starts = [
            current_week - timedelta(weeks=i)
            for i in range(7, -1, -1)
        ]

        return [
            {
                "key": start.isoformat(),
                "label": start.strftime("%b %d"),
                "value": sum(
                    amount
                    for recorded, amount in sales
                    if start
                    <= recorded
                    <= start + timedelta(days=6)
                ),
            }
            for start in starts
        ]

    # --------------------------------------------------------
    # QUARTERLY
    # --------------------------------------------------------

    if period == "quarterly":

        quarter = (
            (today.month - 1) // 3
        ) * 3 + 1

        current_start = date(
            today.year,
            quarter,
            1,
        )

        starts = [
            _shift_month(
                current_start,
                -3 * i,
            )
            for i in range(3, -1, -1)
        ]

        return [
            {
                "key": start.isoformat(),
                "label": (
                    f"Q{((start.month - 1) // 3) + 1}"
                    f" {start.year}"
                ),
                "value": sum(
                    amount
                    for recorded, amount in sales
                    if start
                    <= recorded
                    < _shift_month(start, 3)
                ),
            }
            for start in starts
        ]

    # --------------------------------------------------------
    # MONTHLY
    # --------------------------------------------------------

    current_month = today.replace(day=1)

    starts = [
        _shift_month(
            current_month,
            -i,
        )
        for i in range(4, -1, -1)
    ]

    return [
        {
            "key": start.isoformat(),
            "label": start.strftime("%b %Y"),
            "value": sum(
                amount
                for recorded, amount in sales
                if start
                <= recorded
                < _shift_month(start, 1)
            ),
        }
        for start in starts
    ]


def _monthly_history(
    sales: list[tuple[date, float]],
    count: int,
) -> list[tuple[str, float]]:
    """
    Return the selected number of calendar months,
    including the current month.

    Example:

    Current month = August 2026
    count = 2

    Result:
        July 2026
        August 2026
    """

    current_month = date.today().replace(day=1)

    starts = [
        _shift_month(
            current_month,
            -i,
        )
        for i in range(count - 1, -1, -1)
    ]

    return [
        (
            start.strftime("%B %Y"),
            sum(
                amount
                for recorded, amount in sales
                if start
                <= recorded
                < _shift_month(start, 1)
            ),
        )
        for start in starts
    ]


# ============================================================
# AUTOREGRESSIVE FORECAST
# ============================================================

def _autoregressive_forecast(
    values: list[float],
) -> float:
    """
    Forecast one step using a first-order autoregressive model, AR(1).

    The existing analytics workflow is preserved, but the calculation now uses:
    - Pandas to organize the historical observations as a time series.
    - NumPy to convert and validate the numerical observations.
    - Statsmodels AutoReg to fit the AR(1) forecasting model.

    A small fallback is retained for very short, invalid, or constant datasets so
    the current UI continues to behave safely with incomplete historical data.
    """
    if not values:
        return 0.0

    # Pandas: represent the historical sales values as an ordered Series.
    series = pd.Series(values, dtype="float64").dropna()

    if series.empty:
        return 0.0

    # NumPy: create the numeric array used by the forecasting model.
    observations = np.asarray(series.to_numpy(), dtype=float)
    observations = observations[np.isfinite(observations)]

    if observations.size == 0:
        return 0.0

    if observations.size == 1:
        return max(0.0, float(observations[0]))

    # AutoReg cannot reliably estimate a meaningful AR(1) model from constant
    # observations, so retain a stable numerical fallback.
    if np.allclose(observations, observations[0]):
        return max(0.0, float(np.mean(observations)))

    try:
        # Statsmodels: fit the AR(1) model and forecast the next period.
        model = AutoReg(
            observations,
            lags=1,
            trend="c",
            old_names=False,
        ).fit()

        forecast = model.predict(
            start=len(observations),
            end=len(observations),
            dynamic=False,
        )

        estimate = float(np.asarray(forecast)[0])

    except Exception:
        # Preserve the previous safe behavior if the model cannot be fitted.
        estimate = float(np.mean(observations))

    return max(0.0, estimate)


# ============================================================
# SALES LINE CHART
# ============================================================

class SalesLineChart(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.series: list[dict[str, Any]] = []

        self.setMinimumHeight(168)
        self.setMaximumHeight(190)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def set_series(
        self,
        series: list[dict[str, Any]],
    ) -> None:

        self.series = series
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        left = 48
        top = 14

        right = max(
            left + 20,
            self.width() - 18,
        )

        bottom = max(
            top + 20,
            self.height() - 34,
        )

        chart = QRectF(
            left,
            top,
            right - left,
            bottom - top,
        )

        # Grid lines
        painter.setPen(
            QPen(
                QColor(255, 255, 255, 18),
                1,
            )
        )

        for row in range(5):

            y = (
                chart.top()
                + chart.height()
                * row
                / 4
            )

            painter.drawLine(
                int(chart.left()),
                int(y),
                int(chart.right()),
                int(y),
            )

        # No data
        if not self.series:

            painter.setPen(
                QColor(MUTED)
            )

            painter.drawText(
                chart,
                Qt.AlignmentFlag.AlignCenter,
                "No sales data available",
            )

            painter.end()
            return

        values = [
            float(item["value"])
            for item in self.series
        ]

        scale_max = (
            max(values)
            if max(values) > 0
            else 1
        )

        points = []

        for index, value in enumerate(values):

            if len(values) == 1:

                x = chart.left()

            else:

                x = (
                    chart.left()
                    + chart.width()
                    * index
                    / (len(values) - 1)
                )

            y = (
                chart.bottom()
                - (
                    value
                    / scale_max
                )
                * chart.height()
            )

            points.append(
                (x, y)
            )

        # Line
        painter.setPen(
            QPen(
                QColor(BLUE),
                3,
            )
        )

        for first, second in zip(
            points,
            points[1:],
        ):

            painter.drawLine(
                int(first[0]),
                int(first[1]),
                int(second[0]),
                int(second[1]),
            )

        # Points and labels
        painter.setFont(
            QFont(
                "Segoe UI",
                9,
            )
        )

        for index, ((x, y), item) in enumerate(
            zip(points, self.series)
        ):

            painter.setBrush(
                QColor("#0B1120")
            )

            painter.setPen(
                QPen(
                    QColor(BLUE),
                    2,
                )
            )

            painter.drawEllipse(
                int(x - 4),
                int(y - 4),
                8,
                8,
            )

            if (
                len(self.series) <= 8
                or index in {
                    0,
                    len(self.series) - 1,
                }
            ):

                painter.setPen(
                    QColor(MUTED)
                )

                painter.drawText(
                    QRectF(
                        x - 50,
                        chart.bottom() + 6,
                        100,
                        24,
                    ),
                    Qt.AlignmentFlag.AlignCenter,
                    str(item["label"]),
                )

        # Y-axis labels
        painter.setPen(
            QColor(MUTED)
        )

        for row in range(5):

            value = (
                scale_max
                * (4 - row)
                / 4
            )

            painter.drawText(
                QRectF(
                    0,
                    chart.top()
                    + chart.height()
                    * row
                    - 8,
                    42,
                    20,
                ),
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter,
                (
                    f"₱{value:,.0f}"
                    if value
                    else "₱0"
                ),
            )

        painter.end()


# ============================================================
# MATPLOTLIB SALES CHART
# ============================================================

class MatplotlibSalesChart(FigureCanvas):
    """Matplotlib chart embedded in the existing PyQt6 analytics UI."""

    def __init__(self, parent=None):
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)
        self.setMinimumSize(720, 360)
        self.figure.set_facecolor("#080D1A")
        self.axes.set_facecolor("#0A1120")

    def set_series(self, series: list[dict[str, Any]]) -> None:
        labels = [str(item.get("label", "")) for item in series]
        values = [float(item.get("value", 0) or 0) for item in series]

        self.axes.clear()
        self.axes.set_facecolor("#0A1120")
        self.axes.plot(
            labels,
            values,
            marker="o",
            linewidth=2.2,
            color="#3B82F6",
            label="Recorded sales",
        )
        self.axes.bar(
            labels,
            values,
            alpha=0.16,
            color="#60A5FA",
            label="Sales volume",
        )

        # Reuse the existing Statsmodels/NumPy forecasting calculation without
        # changing the original forecast controls or result card.
        if len(values) >= 2:
            estimate = _autoregressive_forecast(values)
            forecast_labels = labels + ["Next period"]
            forecast_values = values + [estimate]
            self.axes.plot(
                forecast_labels[-2:],
                forecast_values[-2:],
                linestyle="--",
                linewidth=2,
                marker="o",
                color="#10B981",
                label="AR(1) forecast",
            )

        self.axes.set_title(
            "BlockFlow Sales Analysis",
            color="#F8FAFC",
            fontsize=13,
            pad=12,
        )
        self.axes.set_ylabel("Sales (₱)", color="#CBD5E1")
        self.axes.tick_params(colors="#CBD5E1", labelsize=9)
        for spine in self.axes.spines.values():
            spine.set_color("#334155")
        self.axes.grid(axis="y", color="#334155", alpha=0.35)
        self.axes.legend(
            facecolor="#0A1120",
            edgecolor="#334155",
            labelcolor="#CBD5E1",
        )
        self.figure.tight_layout()
        self.draw_idle()


class MatplotlibSalesChartDialog(QDialog):
    """Optional Matplotlib view; existing charts and workflows remain intact."""

    def __init__(self, series: list[dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("BlockFlow — Matplotlib Sales Chart")
        self.setMinimumSize(820, 470)
        self.setStyleSheet(
            """
            QDialog { background: #080D1A; color: #F8FAFC; }
            QPushButton {
                background: #2563EB; color: white; border: none;
                border-radius: 8px; padding: 8px 14px; font-weight: 600;
            }
            QPushButton:hover { background: #3B82F6; }
            """
        )
        layout = QVBoxLayout(self)
        self.chart = MatplotlibSalesChart(self)
        self.chart.set_series(series)
        layout.addWidget(self.chart)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(close_button)
        layout.addLayout(footer)


# ============================================================
# SALES ANALYTICS REPORT DIALOG
# ============================================================

class SalesAnalyticsReportDialog(QDialog):

    def __init__(
        self,
        records: list[dict[str, Any]],
        parent=None,
    ):

        super().__init__(parent)

        self.records = records
        self.period = "monthly"

        self.series: list[
            dict[str, Any]
        ] = []

        self.setWindowTitle(
            "Sales Analytics Report"
        )

        self.setMinimumSize(
            720,
            560,
        )

        self.setStyleSheet(
            """
            QDialog {
                background: #080D1A;
                color: #F8FAFC;
                border: 1px solid rgba(255,255,255,18);
            }

            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
            }

            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 9px 14px;
                font-weight: 600;
            }
            """
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            22,
            18,
            22,
            20,
        )

        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()

        title = QLabel(
            "Sales Analytics Report"
        )

        title.setFont(
            QFont(
                "Segoe UI",
                18,
                QFont.Weight.Bold,
            )
        )

        header.addWidget(title)
        header.addStretch()

        close = QPushButton("✕")

        close.setFixedSize(
            32,
            32,
        )

        close.clicked.connect(
            self.reject
        )

        header.addWidget(close)

        layout.addLayout(header)

        # Period buttons
        period_row = QHBoxLayout()

        period_label = QLabel(
            "Report period"
        )

        period_label.setStyleSheet(
            "color: #CBD5E1;"
        )

        period_row.addWidget(
            period_label
        )

        self.period_buttons = {}

        for label, value in (
            ("Weekly", "weekly"),
            ("Monthly", "monthly"),
            ("Quarterly", "quarterly"),
        ):

            button = QPushButton(
                label
            )

            button.setCheckable(True)

            button.clicked.connect(
                lambda _checked,
                selected=value:
                self.select_period(
                    selected
                )
            )

            self.period_buttons[
                value
            ] = button

            period_row.addWidget(
                button
            )

        period_row.addStretch()

        layout.addLayout(
            period_row
        )

        # Chart title
        self.chart_title = QLabel()

        self.chart_title.setFont(
            QFont(
                "Segoe UI",
                14,
                QFont.Weight.Bold,
            )
        )

        layout.addWidget(
            self.chart_title
        )

        # Chart
        self.chart = SalesLineChart()

        layout.addWidget(
            self.chart
        )

        # Peak
        self.peak = QLabel()

        self.peak.setStyleSheet(
            """
            QLabel {
                background: rgba(37,99,235,80);
                color: #DBEAFE;
                border: 1px solid rgba(96,165,250,120);
                border-radius: 8px;
                padding: 9px;
            }
            """
        )

        layout.addWidget(
            self.peak
        )

        # Summary cards
        summary_row = QHBoxLayout()
        summary_row.setSpacing(8)

        self.total_sales = self._summary_card(
            summary_row,
            "Total Sales",
            "#10B981",
        )
        self.average_sales = self._summary_card(
            summary_row,
            "Average per Period",
            "#60A5FA",
        )
        self.period_count = self._summary_card(
            summary_row,
            "Periods",
            "#A78BFA",
        )

        layout.addLayout(
            summary_row
        )

        # Gemini-ready insights section. Gemini response text is inserted here
        # after the AI request completes; no simulated response is shown.
        insights_title = QLabel(
            "ⓘ  Prescriptive Analytics & Recommendations"
        )
        insights_title.setFont(
            QFont(
                "Segoe UI",
                12,
                QFont.Weight.Bold,
            )
        )
        insights_title.setStyleSheet(
            """
            QLabel {
                color: #F8FAFC;
                padding-top: 4px;
            }
            """
        )
        layout.addWidget(
            insights_title
        )

        self.ai_insights = QLabel()
        self.ai_insights.setWordWrap(
            True
        )
        self.ai_insights.setMinimumHeight(
            62
        )
        self.ai_insights.setStyleSheet(
            """
            QLabel {
                background: rgba(67,56,202,110);
                color: #E0E7FF;
                border: 1px solid rgba(129,140,248,130);
                border-radius: 8px;
                padding: 12px;
            }
            """
        )
        layout.addWidget(
            self.ai_insights
        )

        # Footer
        footer = QHBoxLayout()

        footer.addStretch()

        export = QPushButton(
            "Export CSV"
        )

        export.setStyleSheet(
            """
            QPushButton {
                background: #2563EB;
                color: white;
            }

            QPushButton:hover {
                background: #3B82F6;
            }
            """
        )

        export.clicked.connect(
            self.export_csv
        )

        footer.addWidget(
            export
        )

        layout.addLayout(
            footer
        )

        self.update_report()

    def _summary_card(
        self,
        parent_layout: QHBoxLayout,
        title: str,
        accent: str,
    ) -> QLabel:
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background: rgba(15,23,42,220);
                border: 1px solid rgba(148,163,184,45);
                border-left: 3px solid {accent};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )
        card_layout.setSpacing(
            2
        )

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color: #94A3B8; font-size: 10px;"
        )
        value_label = QLabel("₱0.00")
        value_label.setStyleSheet(
            f"color: {accent}; font-size: 16px; font-weight: 700;"
        )
        card_layout.addWidget(
            title_label
        )
        card_layout.addWidget(
            value_label
        )
        parent_layout.addWidget(
            card
        )
        return value_label

    def set_ai_insight(self, response_text: str) -> None:
        """Display the actual response returned by the Gemini integration."""
        self.ai_insights.setText(
            response_text.strip()
        )

    def select_period(
        self,
        period: str,
    ):

        self.period = period

        self.update_report()

    def update_report(self):

        self.series = _series_for_period(
            _sales_records(
                self.records
            ),
            self.period,
        )

        for key, button in (
            self.period_buttons.items()
        ):

            button.setChecked(
                key == self.period
            )

            button.setStyleSheet(
                """
                QPushButton {
                    background: %s;
                    color: white;
                }

                QPushButton:unchecked {
                    background: rgba(255,255,255,8);
                    color: #CBD5E1;
                }

                QPushButton:hover {
                    background: #3B82F6;
                    color: white;
                }
                """
                % (
                    BLUE_DARK
                    if key == self.period
                    else "rgba(255,255,255,8)"
                )
            )

        self.chart_title.setText(
            f"▥  Sales Time Series Analysis — "
            f"{self.period.capitalize()}"
        )

        self.chart.set_series(
            self.series
        )

        peak = max(
            self.series,
            key=lambda item:
            item["value"],
            default={
                "label": "N/A",
                "value": 0,
            },
        )

        self.peak.setText(
            f"Peak period: "
            f"{peak['label']} "
            f"with ₱{peak['value']:,.0f} "
            f"in sales"
        )

        values = [
            float(item.get("value", 0) or 0)
            for item in self.series
        ]
        total = sum(values)
        average = total / len(values) if values else 0.0

        self.total_sales.setText(
            f"₱{total:,.2f}"
        )
        self.average_sales.setText(
            f"₱{average:,.2f}"
        )
        self.period_count.setText(
            str(len(values))
        )

        # Keep this panel empty until the Gemini integration supplies the
        # actual response for the selected report period.
        self.ai_insights.clear()

    def export_csv(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sales Report",
            "sales_report.csv",
            "CSV files (*.csv)",
        )

        if not path:
            return

        with open(
            path,
            "w",
            newline="",
            encoding="utf-8",
        ) as report_file:

            writer = csv.writer(
                report_file
            )

            writer.writerow(
                [
                    "Period",
                    "Sales",
                ]
            )

            writer.writerows(
                (
                    item["label"],
                    f"{item['value']:.2f}",
                )
                for item in self.series
            )


# ============================================================
# BLOCKFLOW ANALYTICS
# ============================================================

class BlockFlowAnalytics(QFrame):

    def __init__(
        self,
        role: str = "owner",
    ):

        super().__init__()

        self.setFont(
            QFont(
                "Segoe UI",
                10,
            )
        )

        self.role = role

        self.setWindowTitle(
            "BlockFlow — Analytics"
        )

        self.setObjectName(
            "AnalyticsWindow"
        )

        self.setStyleSheet(
            """
            QFrame#AnalyticsWindow {
                background: transparent;
                color: #F8FAFC;
            }

            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
            }

            QLabel[muted="true"] {
                color: #CBD5E1;
            }

            QLineEdit {
                color: #F8FAFC;
            }
            """
        )

        current_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        self.image_path = os.path.join(
            current_dir,
            "image_b08741.png",
        )

        if not os.path.exists(
            self.image_path
        ):

            self.image_path = os.path.join(
                current_dir,
                "image_b08741.jpg",
            )

        self.records: list[
            dict[str, Any]
        ] = []

        self.init_ui()

        self.reload_data()

        self.showFullScreen()

    # ========================================================
    # BACKGROUND
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            QColor("#080D1A"),
        )

        pixmap = QPixmap(
            self.image_path
        )

        if not pixmap.isNull():

            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )

            painter.drawPixmap(
                (
                    self.width()
                    - scaled.width()
                )
                // 2,
                (
                    self.height()
                    - scaled.height()
                )
                // 2,
                scaled,
            )

            # Dark overlay matching Inventory
            painter.fillRect(
                self.rect(),
                QColor(
                    5,
                    10,
                    25,
                    205,
                ),
            )

        painter.end()

    # ========================================================
    # NAVIGATION BUTTON
    # ========================================================

    def _nav_button(
        self,
        text: str,
        active: bool = False,
    ) -> QPushButton:

        button = QPushButton(text)

        button.setFixedHeight(34)

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setStyleSheet(
            """
            QPushButton {
                background: %s;
                color: %s;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: rgba(255,255,255,10);
                color: #F8FAFC;
            }
            """
            % (
                "rgba(59,130,246,35)"
                if active
                else "transparent",

                "#93C5FD"
                if active
                else "#CBD5E1",
            )
        )

        return button

    # ========================================================
    # UI
    # ========================================================

    def init_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        root.setSpacing(0)

        # ====================================================
        # NAVIGATION
        # ====================================================

        nav = QFrame()

        nav.setFixedHeight(64)

        nav.setStyleSheet(
            """
            QFrame {
                background: rgba(6,10,22,235);
                border-bottom: 1px solid rgba(255,255,255,10);
            }
            """
        )

        nav_layout = QHBoxLayout(nav)

        nav_layout.setContentsMargins(
            28,
            0,
            28,
            0,
        )

        nav_layout.setSpacing(0)

        brand_badge = QLabel("BF")

        brand_badge.setFixedSize(
            34,
            34,
        )

        brand_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        brand_badge.setFont(
            QFont(
                "Segoe UI",
                12,
                QFont.Weight.Bold,
            )
        )

        brand_badge.setStyleSheet(
            """
            QLabel {
                color: white;
                background: qlineargradient(
                    x1:0,
                    y1:0,
                    x2:1,
                    y2:1,
                    stop:0 #3B82F6,
                    stop:1 #8B5CF6
                );
                border-radius: 9px;
            }
            """
        )

        brand_label = QLabel(
            "BlockFlow"
        )

        brand_label.setFont(
            QFont(
                "Segoe UI",
                15,
                QFont.Weight.Bold,
            )
        )

        brand_label.setStyleSheet(
            """
            QLabel {
                color: #F8FAFC;
                padding-left: 10px;
            }
            """
        )

        nav_layout.addWidget(
            brand_badge
        )

        nav_layout.addWidget(
            brand_label
        )

        nav_layout.addSpacing(36)

        separator = QFrame()

        separator.setFixedSize(
            1,
            28,
        )

        separator.setStyleSheet(
            """
            QFrame {
                background: rgba(255,255,255,10);
            }
            """
        )

        nav_layout.addWidget(
            separator
        )

        nav_layout.addSpacing(28)

        dashboard = self._nav_button(
            "Dashboard"
        )

        dashboard.clicked.connect(
            self.handle_nav_dashboard
        )

        inventory = self._nav_button(
            "Inventory"
        )

        inventory.clicked.connect(
            self.handle_nav_inventory
        )

        analytics = self._nav_button(
            "Analytics",
            True,
        )

        nav_layout.addWidget(
            dashboard
        )

        nav_layout.addSpacing(4)

        nav_layout.addWidget(
            inventory
        )

        nav_layout.addSpacing(4)

        nav_layout.addWidget(
            analytics
        )

        nav_layout.addStretch()

        # Admin
        admin = QLabel(
            "👤  Admin"
            if self.role
            in ("owner", "admin")
            else "👷  Staff"
        )

        admin.setStyleSheet(
            """
            QLabel {
                color: #CBD5E1;
                background: rgba(30,41,59,180);
                padding: 7px 16px;
                border-radius: 18px;
                border: 1px solid rgba(255,255,255,10);
                font-weight: 600;
            }
            """
        )

        # Logout
        logout = QPushButton(
            "Logout"
        )

        logout.setFixedHeight(34)

        logout.setStyleSheet(
            """
            QPushButton {
                color: #CBD5E1;
                background: rgba(30,41,59,160);
                padding: 0 18px;
                border-radius: 17px;
                border: 1px solid rgba(255,255,255,10);
                font-weight: 600;
            }

            QPushButton:hover {
                color: #F87171;
                background: rgba(239,68,68,35);
            }
            """
        )

        logout.clicked.connect(
            self.handle_logout
        )

        nav_layout.addWidget(
            admin
        )

        nav_layout.addSpacing(10)

        nav_layout.addWidget(
            logout
        )

        root.addWidget(nav)

        # ====================================================
        # SCROLL AREA
        # ====================================================

        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: rgba(5,10,20,120);
                width: 10px;
                margin: 2px;
            }

            QScrollBar::handle:vertical {
                background: rgba(148,163,184,100);
                border-radius: 5px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(148,163,184,150);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )

        scroll.viewport().setStyleSheet(
            "background: transparent;"
        )

        workspace = QWidget()

        workspace.setStyleSheet(
            """
            QWidget {
                background: transparent;
            }
            """
        )

        workspace_layout = QVBoxLayout(
            workspace
        )

        workspace_layout.setContentsMargins(
            20,
            22,
            20,
            24,
        )

        workspace_layout.setSpacing(
            12
        )

        workspace_layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
        )

        # ====================================================
        # SALES CHART PANEL
        # ====================================================

        chart_panel = self._panel()

        self.chart_panel = chart_panel

        chart_layout = QVBoxLayout(
            chart_panel
        )

        chart_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        chart_layout.setSpacing(6)

        chart_title = QLabel(
            "▥  Sales Time Series Analysis"
        )

        chart_title.setFont(
            QFont(
                "Segoe UI",
                15,
                QFont.Weight.Bold,
            )
        )

        chart_title.setStyleSheet(
            """
            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
            }
            """
        )

        chart_layout.addWidget(
            chart_title
        )

        subtitle = QLabel(
            "Historical sales by month"
        )

        subtitle.setStyleSheet(
            f"""
            QLabel {{
                color: {MUTED};
                background: transparent;
                border: none;
                font-size: 11px;
            }}
            """
        )

        chart_layout.addWidget(
            subtitle
        )

        self.main_chart = SalesLineChart()

        chart_layout.addWidget(
            self.main_chart
        )

        self.main_peak = QLabel()

        self.main_peak.setStyleSheet(
            """
            QLabel {
                background: rgba(37,99,235,80);
                color: #DBEAFE;
                border: 1px solid rgba(96,165,250,120);
                border-radius: 8px;
                padding: 8px;
                font-weight: 600;
            }
            """
        )

        chart_layout.addWidget(
            self.main_peak
        )

        report_button = QPushButton(
            "▣  Create Report"
        )

        report_button.setFixedHeight(
            34
        )

        report_button.setStyleSheet(
            """
            QPushButton {
                background: #2563EB;
                color: white;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #3B82F6;
            }
            """
        )

        report_button.clicked.connect(
            self.open_report
        )

        matplotlib_button = QPushButton(
            "▥  Matplotlib Chart"
        )

        matplotlib_button.setFixedHeight(
            34
        )

        matplotlib_button.setStyleSheet(
            """
            QPushButton {
                background: rgba(16,185,129,180);
                color: white;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #10B981;
            }
            """
        )

        matplotlib_button.clicked.connect(
            self.open_matplotlib_chart
        )

        button_row = QHBoxLayout()

        button_row.addStretch()

        button_row.addWidget(
            matplotlib_button
        )

        button_row.addWidget(
            report_button
        )

        chart_layout.addLayout(
            button_row
        )

        workspace_layout.addWidget(
            chart_panel,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        # ====================================================
        # FORECAST PANEL
        # ====================================================

        forecast_panel = self._panel()

        self.forecast_panel = forecast_panel

        forecast_layout = QVBoxLayout(
            forecast_panel
        )

        forecast_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        forecast_layout.setSpacing(6)

        forecast_title = QLabel(
            "▣  Autoregressive Sales Forecasting"
        )

        forecast_title.setFont(
            QFont(
                "Segoe UI",
                15,
                QFont.Weight.Bold,
            )
        )

        forecast_title.setStyleSheet(
            """
            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
            }
            """
        )

        forecast_layout.addWidget(
            forecast_title
        )

        forecast_subtitle = QLabel(
            "Input historical sales data to predict "
            "next month's sales using an AR(1) model"
        )

        forecast_subtitle.setStyleSheet(
            """
            QLabel {
                color: #AEBBCB;
                background: transparent;
                border: none;
                font-size: 11px;
            }
            """
        )

        forecast_layout.addWidget(
            forecast_subtitle
        )

        # Current month
        self.forecast_current = QLabel()

        self.forecast_current.setStyleSheet(
            """
            QLabel {
                background: rgba(30,41,59,190);
                color: #F8FAFC;
                border: 1px solid rgba(148,163,184,80);
                border-radius: 8px;
                padding: 8px;
                font-weight: 600;
            }
            """
        )

        forecast_layout.addWidget(
            self.forecast_current
        )

        # Selection label
        selection_label = QLabel(
            "Select Number of Past Months to Use"
        )

        selection_label.setStyleSheet(
            """
            QLabel {
                color: #E2E8F0;
                background: transparent;
                border: none;
                font-weight: 600;
            }
            """
        )

        forecast_layout.addWidget(
            selection_label
        )

        # Month buttons
        month_selector = QHBoxLayout()

        month_selector.setSpacing(8)

        self.forecast_month_group = QButtonGroup(
            self
        )

        self.forecast_month_buttons = {}

        for count in (
            2,
            3,
            4,
            5,
            6,
        ):

            button = QPushButton(
                f"{count} Months"
            )

            button.setCheckable(
                True
            )

            button.setFixedHeight(
                32
            )

            button.clicked.connect(
                self._update_forecast_inputs
            )

            self.forecast_month_group.addButton(
                button,
                count,
            )

            self.forecast_month_buttons[
                count
            ] = button

            month_selector.addWidget(
                button
            )

        month_selector.addStretch()

        self.forecast_month_buttons[
            2
        ].setChecked(True)

        forecast_layout.addLayout(
            month_selector
        )

        # Historical sales title
        history_label = QLabel(
            "Historical Monthly Sales (₱) "
            "— Auto-populated from your transactions"
        )

        history_label.setStyleSheet(
            """
            QLabel {
                color: #E2E8F0;
                background: transparent;
                border: none;
                font-weight: 600;
            }
            """
        )

        forecast_layout.addWidget(
            history_label
        )

        history_hint = QLabel(
            "Values come from recorded sales. "
            "You can edit these values if needed."
        )

        history_hint.setStyleSheet(
            """
            QLabel {
                color: #94A3B8;
                background: transparent;
                border: none;
                font-size: 11px;
            }
            """
        )

        forecast_layout.addWidget(
            history_hint
        )

        # Historical input grid
        self.forecast_inputs_layout = QGridLayout()

        self.forecast_inputs_layout.setHorizontalSpacing(
            12
        )

        self.forecast_inputs_layout.setVerticalSpacing(
            4
        )

        self.forecast_inputs = []

        forecast_layout.addLayout(
            self.forecast_inputs_layout
        )

        # Calculate button
        calculate = QPushButton(
            "⌁  Calculate Forecast"
        )

        calculate.setFixedHeight(
            36
        )

        calculate.setStyleSheet(
            """
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #3B82F6;
            }

            QPushButton:pressed {
                background: #1D4ED8;
            }
            """
        )

        calculate.clicked.connect(
            self.calculate_forecast
        )

        forecast_layout.addWidget(
            calculate,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        # ====================================================
        # FORECAST RESULT CARD
        #
        # IMPORTANT:
        # Only the outer QFrame has a border.
        # The labels inside have NO border.
        # ====================================================

        self.forecast_result = QFrame()

        self.forecast_result.setObjectName(
            "ForecastResultCard"
        )

        self.forecast_result.setStyleSheet(
            """
            QFrame#ForecastResultCard {
                background: rgba(5,150,105,65);
                border: 1px solid rgba(16,185,129,180);
                border-radius: 10px;
            }
            """
        )

        result_layout = QVBoxLayout(
            self.forecast_result
        )

        result_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        result_layout.setSpacing(
            2
        )

        # Header
        result_header = QHBoxLayout()

        result_header.setSpacing(
            10
        )

        # Icon
        result_icon = QLabel(
            "↗"
        )

        result_icon.setFixedSize(
            34,
            34,
        )

        result_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        result_icon.setStyleSheet(
            """
            QLabel {
                background: #10B981;
                color: white;
                border: none;
                border-radius: 17px;
                font-size: 18px;
                font-weight: bold;
            }
            """
        )

        result_header.addWidget(
            result_icon
        )

        # Title and subtitle
        result_text_layout = QVBoxLayout()

        result_text_layout.setSpacing(
            0
        )

        self.forecast_title = QLabel(
            "Predicted Sales"
        )

        self.forecast_title.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: #ECFDF5;
                font-size: 14px;
                font-weight: 700;
                padding: 0;
                margin: 0;
            }
            """
        )

        self.forecast_subtitle_result = QLabel(
            "Next Month Forecast"
        )

        self.forecast_subtitle_result.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: #A7F3D0;
                font-size: 10px;
                padding: 0;
                margin: 0;
            }
            """
        )

        result_text_layout.addWidget(
            self.forecast_title
        )

        result_text_layout.addWidget(
            self.forecast_subtitle_result
        )

        result_header.addLayout(
            result_text_layout
        )

        result_header.addStretch()

        result_layout.addLayout(
            result_header
        )

        # Amount
        self.forecast_amount = QLabel(
            "₱0.00"
        )

        self.forecast_amount.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: #A7F3D0;
                font-size: 25px;
                font-weight: 800;
                padding: 4px 0 0 0;
                margin: 0;
            }
            """
        )

        result_layout.addWidget(
            self.forecast_amount
        )

        # Model information
        self.forecast_model_info = QLabel(
            "Calculate a forecast to see the estimate."
        )

        self.forecast_model_info.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: #86EFAC;
                font-size: 10px;
                padding: 2px 0 0 0;
                margin: 0;
            }
            """
        )

        result_layout.addWidget(
            self.forecast_model_info
        )

        # Hide result initially
        self.forecast_result.setVisible(
            False
        )

        forecast_layout.addWidget(
            self.forecast_result
        )

        # ====================================================
        # FINISH FORECAST PANEL
        # ====================================================

        self._update_forecast_inputs()

        workspace_layout.addWidget(
            forecast_panel,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        scroll.setWidget(
            workspace
        )

        root.addWidget(
            scroll
        )

    # ========================================================
    # RESPONSIVE WIDTH
    # ========================================================

    def resizeEvent(
        self,
        event,
    ):

        super().resizeEvent(
            event
        )

        if (
            hasattr(
                self,
                "chart_panel",
            )
            and hasattr(
                self,
                "forecast_panel",
            )
        ):

            panel_width = max(
                380,
                int(
                    self.width()
                    * 0.70
                ),
            )

            panel_width = min(
                panel_width,
                max(
                    380,
                    self.width() - 40,
                ),
            )

            self.chart_panel.setFixedWidth(
                panel_width
            )

            self.forecast_panel.setFixedWidth(
                panel_width
            )

    # ========================================================
    # PANEL STYLE
    # ========================================================

    def _panel(self) -> QFrame:

        panel = QFrame()

        panel.setStyleSheet(
            f"""
            QFrame {{
                background: {PANEL};
                border: 1px solid rgba(255,255,255,12);
                border-radius: 14px;
            }}

            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

        return panel

    # ========================================================
    # LOAD DATABASE DATA
    # ========================================================

    def reload_data(self):

        try:

            self.records = _load_transaction_history()

        except Exception:

            self.records = []

        sales = _sales_records(
            self.records
        )

        # Main chart
        series = _series_for_period(
            sales,
            "monthly",
        )

        self.main_chart.set_series(
            series
        )

        peak = max(
            series,
            key=lambda item:
            item["value"],
            default={
                "label": "N/A",
                "value": 0,
            },
        )

        self.main_peak.setText(
            f"Peak month: "
            f"{peak['label']} "
            f"with ₱{peak['value']:,.0f} "
            f"in sales"
        )

        # Current month
        self.forecast_current.setText(
            f"Current Month: "
            f"{date.today().strftime('%B %Y')}"
        )

        # Refresh historical inputs
        self._update_forecast_inputs()

    # ========================================================
    # REPORT
    # ========================================================

    def open_report(self):

        SalesAnalyticsReportDialog(
            self.records,
            self,
        ).exec()

    def open_matplotlib_chart(self):

        series = _series_for_period(
            _sales_records(self.records),
            "monthly",
        )

        MatplotlibSalesChartDialog(
            series,
            self,
        ).exec()

    # ========================================================
    # CALCULATE FORECAST
    # ========================================================

    def calculate_forecast(self):

        values = []

        for field in self.forecast_inputs:

            try:

                value = float(
                    field.text()
                    .replace(",", "")
                    .replace("₱", "")
                    .strip()
                    or 0
                )

            except ValueError:

                self._show_forecast_error(
                    "Please enter valid numeric sales values."
                )

                return

            if value < 0:

                self._show_forecast_error(
                    "Sales values cannot be negative."
                )

                return

            values.append(
                value
            )

        if not values:

            self._show_forecast_error(
                "Please enter historical sales values."
            )

            return

        # Calculate AR(1)
        estimate = _autoregressive_forecast(
            values
        )

        # Automatically calculate next month
        current_month = date.today().replace(
            day=1
        )

        next_month = _shift_month(
            current_month,
            1,
        )

        next_month_label = (
            next_month.strftime(
                "%B %Y"
            )
        )

        # Update prediction card
        self.forecast_title.setText(
            f"Predicted Sales for "
            f"{next_month_label}"
        )

        self.forecast_subtitle_result.setText(
            "Next Month Forecast"
        )

        self.forecast_amount.setText(
            f"₱{estimate:,.2f}"
        )

        self.forecast_model_info.setText(
            f"Based on AR(1) model using "
            f"{len(values)} month(s) of "
            f"historical data"
        )

        # Show result
        self.forecast_result.setVisible(
            True
        )

    # ========================================================
    # FORECAST ERROR
    # ========================================================

    def _show_forecast_error(
        self,
        message: str,
    ):

        self.forecast_result.setVisible(
            True
        )

        self.forecast_title.setText(
            "Forecast Error"
        )

        self.forecast_subtitle_result.setText(
            "Please check the historical values"
        )

        self.forecast_amount.setText(
            ""
        )

        self.forecast_model_info.setText(
            message
        )

        self.forecast_result.setStyleSheet(
            """
            QFrame#ForecastResultCard {
                background: rgba(127,29,29,65);
                border: 1px solid rgba(248,113,113,170);
                border-radius: 10px;
            }
            """
        )

        self.forecast_title.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: #FECACA;
                font-size: 14px;
                font-weight: 700;
                padding: 0;
                margin: 0;
            }
            """
        )

        self.forecast_subtitle_result.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: #FCA5A5;
                font-size: 10px;
                padding: 0;
                margin: 0;
            }
            """
        )

        self.forecast_model_info.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: #FCA5A5;
                font-size: 10px;
                padding: 2px 0 0 0;
                margin: 0;
            }
            """
        )

    # ========================================================
    # UPDATE FORECAST INPUTS
    # ========================================================

    def _update_forecast_inputs(
        self,
    ):

        count = (
            self.forecast_month_group.checkedId()
            or 2
        )

        # Clear existing widgets
        while (
            self.forecast_inputs_layout.count()
        ):

            item = (
                self.forecast_inputs_layout.takeAt(
                    0
                )
            )

            if item.widget():

                item.widget().deleteLater()

            elif item.layout():

                while item.layout().count():

                    child = (
                        item.layout().takeAt(
                            0
                        )
                    )

                    if child.widget():

                        child.widget().deleteLater()

        self.forecast_inputs = []

        # Get sales from database
        monthly = _monthly_history(
            _sales_records(
                self.records
            ),
            count,
        )

        # Update selected button styling
        for button_count, button in (
            self.forecast_month_buttons.items()
        ):

            selected = (
                button_count
                == count
            )

            button.setChecked(
                selected
            )

            button.setStyleSheet(
                """
                QPushButton {
                    background: %s;
                    color: %s;
                    border: 1px solid %s;
                    border-radius: 8px;
                    padding: 0 12px;
                    font-weight: 600;
                }

                QPushButton:hover {
                    background: #3B82F6;
                    color: white;
                    border: 1px solid #60A5FA;
                }
                """
                % (
                    BLUE_DARK
                    if selected
                    else "rgba(30,41,59,210)",

                    "#FFFFFF"
                    if selected
                    else "#CBD5E1",

                    "#60A5FA"
                    if selected
                    else "rgba(148,163,184,80)",
                )
            )

        # Create input boxes
        for index, (
            label,
            value,
        ) in enumerate(monthly):

            column = QVBoxLayout()

            column.setSpacing(
                4
            )

            label_widget = QLabel(
                label
            )

            label_widget.setStyleSheet(
                """
                QLabel {
                    color: #CBD5E1;
                    background: transparent;
                    border: none;
                    font-weight: 600;
                    font-size: 11px;
                    padding: 0;
                }
                """
            )

            field = QLineEdit(
                f"{value:.2f}"
            )

            field.setPlaceholderText(
                "0.00"
            )

            field.setFixedHeight(
                34
            )

            field.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            field.setStyleSheet(
                """
                QLineEdit {
                    background: rgba(15,23,42,235);
                    color: #F8FAFC;
                    border: 1px solid rgba(148,163,184,110);
                    border-radius: 7px;
                    padding: 7px;
                    font-size: 12px;
                }

                QLineEdit:focus {
                    border: 1px solid #60A5FA;
                    background: rgba(15,23,42,245);
                }

                QLineEdit:hover {
                    border: 1px solid rgba(148,163,184,160);
                }
                """
            )

            column.addWidget(
                label_widget
            )

            column.addWidget(
                field
            )

            self.forecast_inputs_layout.addLayout(
                column,
                0,
                index,
            )

            self.forecast_inputs.append(
                field
            )

        # Hide old result when changing number of months
        if hasattr(
            self,
            "forecast_result",
        ):

            self.forecast_result.setVisible(
                False
            )

            # Restore normal green styling
            self.forecast_result.setStyleSheet(
                """
                QFrame#ForecastResultCard {
                    background: rgba(5,150,105,65);
                    border: 1px solid rgba(16,185,129,180);
                    border-radius: 10px;
                }
                """
            )

            self.forecast_title.setStyleSheet(
                """
                QLabel {
                    background: transparent;
                    border: none;
                    color: #ECFDF5;
                    font-size: 14px;
                    font-weight: 700;
                    padding: 0;
                    margin: 0;
                }
                """
            )

            self.forecast_subtitle_result.setStyleSheet(
                """
                QLabel {
                    background: transparent;
                    border: none;
                    color: #A7F3D0;
                    font-size: 10px;
                    padding: 0;
                    margin: 0;
                }
                """
            )

            self.forecast_amount.setStyleSheet(
                """
                QLabel {
                    background: transparent;
                    border: none;
                    color: #A7F3D0;
                    font-size: 25px;
                    font-weight: 800;
                    padding: 4px 0 0 0;
                    margin: 0;
                }
                """
            )

            self.forecast_model_info.setStyleSheet(
                """
                QLabel {
                    background: transparent;
                    border: none;
                    color: #86EFAC;
                    font-size: 10px;
                    padding: 2px 0 0 0;
                    margin: 0;
                }
                """
            )

    # ========================================================
    # NAVIGATION
    # ========================================================

    def handle_nav_dashboard(
        self,
    ):

        from dashboard_view import (
            BlockFlowDashboard,
        )

        self.dashboard_window = (
            BlockFlowDashboard()
        )

        self.dashboard_window.show()

        self.close()

    def handle_nav_inventory(
        self,
    ):

        from inventory_view import (
            BlockFlowInventory,
        )

        self.inventory_window = (
            BlockFlowInventory(
                role=self.role
            )
        )

        self.inventory_window.show()

        self.close()

    # ========================================================
    # LOGOUT
    # ========================================================

    def handle_logout(
        self,
    ):

        from login_view import (
            BlockFlowLogin,
        )

        self.login_window = (
            BlockFlowLogin()
        )

        self.login_window.show()

        self.close()

    # ========================================================
    # ESCAPE
    # ========================================================

    def keyPressEvent(
        self,
        event,
    ):

        if event.key() == Qt.Key.Key_Escape:

            self.close()

        else:

            super().keyPressEvent(
                event
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    app.setFont(
        QFont(
            "Segoe UI",
            10,
        )
    )

    window = BlockFlowAnalytics()

    window.show()

    sys.exit(
        app.exec()
    )