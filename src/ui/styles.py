from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

PALETTE = {
    "bg_main": "#2E2E2E",
    "bg_card": "#2A2A2A",
    "bg_input": "#3A3A3A",
    "text_main": "#CCCCCC",
    "text_bright": "#FFFFFF",
    "text_dim": "#888888",
    "accent_blue": "#3DAEE9",
    "accent_gold": "#C9A227",
    "accent_gold_text": "#FFD700",
    "accent_green_bg": "#2A4A2A",
    "accent_green_text": "#90EE90",
    "accent_red_bg": "#4A2A2A",
    "accent_red_text": "#FF6B6B",
    "accent_neutral_bg": "#2E2E2E",
    "accent_neutral_text": "#CCCCCC",
    "border": "#4A4A4A",
    "metric_improved": "#90EE90",
    "metric_worsened": "#FF6B6B",
    "metric_unchanged": "#888888",
}

QSS = f"""
QMainWindow, QDialog, QWidget {{
    background-color: {PALETTE['bg_main']};
    color: {PALETTE['text_main']};
    font-family: "Noto Sans", "Sans";
    font-size: 10pt;
}}
QMenuBar, QMenu {{
    background-color: {PALETTE['bg_input']};
    color: {PALETTE['text_main']};
    border: 1px solid {PALETTE['border']};
}}
QMenuBar::item:selected, QMenu::item:selected {{
    background-color: {PALETTE['accent_blue']};
    color: {PALETTE['text_bright']};
}}
QToolBar {{
    background-color: {PALETTE['bg_card']};
    border-bottom: 1px solid {PALETTE['border']};
    spacing: 6px;
    padding: 4px;
}}
QStatusBar {{
    background-color: {PALETTE['bg_card']};
    color: {PALETTE['text_dim']};
}}
QPushButton, QToolButton {{
    background-color: {PALETTE['bg_input']};
    border: 1px solid {PALETTE['border']};
    border-radius: 4px;
}}
QPushButton:hover, QToolButton:hover {{
    background-color: #4A4A4A;
    border-color: {PALETTE['accent_blue']};
}}
QPushButton:default {{
    background-color: {PALETTE['accent_blue']};
    color: {PALETTE['text_bright']};
    border-color: {PALETTE['accent_blue']};
}}
QPushButton:disabled {{
    color: #666666;
    background-color: #303030;
}}
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QTextEdit, QDateEdit {{
    background-color: {PALETTE['bg_input']};
    border: 1px solid {PALETTE['border']};
    border-radius: 3px;
    padding: 4px;
    color: {PALETTE['text_main']};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus {{
    border-color: {PALETTE['accent_blue']};
}}
QTextEdit[readOnly="true"] {{
    background-color: transparent;
    border: none;
}}
QTableView, QTableWidget {{
    background-color: {PALETTE['bg_main']};
    alternate-background-color: {PALETTE['bg_input']};
    gridline-color: {PALETTE['border']};
    selection-background-color: {PALETTE['accent_blue']};
    selection-color: {PALETTE['text_bright']};
}}
QHeaderView::section {{
    background-color: {PALETTE['bg_input']};
    color: {PALETTE['text_main']};
    padding: 6px;
    border: 1px solid {PALETTE['border']};
}}
QGroupBox {{
    border: 1px solid {PALETTE['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 12px;
    color: {PALETTE['text_main']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QSplitter::handle {{
    background-color: {PALETTE['border']};
}}
QTabWidget::pane {{
    border: 1px solid {PALETTE['border']};
}}
QTabBar::tab {{
    background-color: {PALETTE['bg_input']};
    color: {PALETTE['text_main']};
    padding: 8px 14px;
    border: 1px solid {PALETTE['border']};
}}
QTabBar::tab:selected {{
    background-color: {PALETTE['accent_blue']};
    color: {PALETTE['text_bright']};
}}
QFrame#ResultFrame, QFrame#DetailCard {{
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
}}
"""


def apply_breeze_dark(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Noto Sans", 10))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(PALETTE["bg_main"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(PALETTE["text_main"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(PALETTE["bg_main"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(PALETTE["bg_input"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(PALETTE["bg_input"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(PALETTE["text_bright"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(PALETTE["text_main"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(PALETTE["bg_input"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(PALETTE["text_main"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(PALETTE["accent_red_text"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(PALETTE["accent_blue"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(PALETTE["accent_blue"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(PALETTE["text_bright"]))
    app.setPalette(palette)
    app.setStyleSheet(QSS)
