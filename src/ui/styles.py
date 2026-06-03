from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from src.config import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    PALETTE,
)

# ============================================================
# GLOBAL QSS
# ============================================================

GLOBAL_STYLESHEET = f"""
QMainWindow,
QDialog,
QWidget {{
    background-color: {PALETTE["bg_main"]};
    color: {PALETTE["text_main"]};
    font-family: "{DEFAULT_FONT_FAMILY}";
    font-size: {DEFAULT_FONT_SIZE}pt;
}}

QPushButton {{
    background-color: {PALETTE["bg_input"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 4px;
    padding: 6px 16px;
    color: {PALETTE["text_main"]};
}}

QPushButton:hover {{
    border-color: {PALETTE["accent_blue"]};
    background-color: #454545;
}}

QPushButton:pressed {{
    background-color: #505050;
}}

QPushButton:disabled {{
    background-color: #2A2A2A;
    color: #777777;
    border-color: #3A3A3A;
}}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox,
QDateEdit,
QSpinBox,
QDoubleSpinBox {{
    background-color: {PALETTE["bg_input"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 4px;
    padding: 4px;
    color: {PALETTE["text_main"]};
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus,
QDateEdit:focus {{
    border-color: {PALETTE["accent_blue"]};
}}

QTableView {{
    background-color: {PALETTE["bg_main"]};
    alternate-background-color: #353535;
    gridline-color: {PALETTE["border"]};
    border: 1px solid {PALETTE["border"]};
    selection-background-color: {PALETTE["accent_blue"]};
    selection-color: white;
}}

QHeaderView::section {{
    background-color: {PALETTE["bg_input"]};
    color: {PALETTE["text_main"]};
    padding: 6px;
    border: 1px solid {PALETTE["border"]};
}}

QMenuBar {{
    background-color: {PALETTE["bg_card"]};
}}

QMenuBar::item:selected {{
    background-color: {PALETTE["accent_blue"]};
}}

QMenu {{
    background-color: {PALETTE["bg_card"]};
    border: 1px solid {PALETTE["border"]};
}}

QMenu::item:selected {{
    background-color: {PALETTE["accent_blue"]};
}}

QToolBar {{
    spacing: 6px;
    padding: 4px;
    border-bottom: 1px solid {PALETTE["border"]};
}}

QStatusBar {{
    background-color: {PALETTE["bg_card"]};
    border-top: 1px solid {PALETTE["border"]};
}}

QGroupBox {{
    border: 1px solid {PALETTE["border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px 0 4px;
}}
"""


# ============================================================
# APPLY THEME
# ============================================================


def apply_theme(app: QApplication) -> None:
    """
    Nakłada globalny styl aplikacji.
    """

    # ========================================================
    # FONT
    # ========================================================

    font = QFont(
        DEFAULT_FONT_FAMILY,
        DEFAULT_FONT_SIZE,
    )

    app.setFont(font)

    # ========================================================
    # PALETTE
    # ========================================================

    palette = QPalette()

    palette.setColor(
        QPalette.Window,
        QColor(PALETTE["bg_main"]),
    )

    palette.setColor(
        QPalette.WindowText,
        QColor(PALETTE["text_main"]),
    )

    palette.setColor(
        QPalette.Base,
        QColor(PALETTE["bg_input"]),
    )

    palette.setColor(
        QPalette.AlternateBase,
        QColor(PALETTE["bg_card"]),
    )

    palette.setColor(
        QPalette.ToolTipBase,
        QColor(PALETTE["bg_card"]),
    )

    palette.setColor(
        QPalette.ToolTipText,
        QColor(PALETTE["text_main"]),
    )

    palette.setColor(
        QPalette.Text,
        QColor(PALETTE["text_main"]),
    )

    palette.setColor(
        QPalette.Button,
        QColor(PALETTE["bg_input"]),
    )

    palette.setColor(
        QPalette.ButtonText,
        QColor(PALETTE["text_main"]),
    )

    palette.setColor(
        QPalette.Highlight,
        QColor(PALETTE["accent_blue"]),
    )

    palette.setColor(
        QPalette.HighlightedText,
        QColor("#FFFFFF"),
    )

    app.setPalette(palette)

    # ========================================================
    # QSS
    # ========================================================

    app.setStyleSheet(GLOBAL_STYLESHEET)
