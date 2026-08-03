from __future__ import annotations

from pathlib import Path

APP_NAME = "Dziennik Inwestora Value"
APP_VERSION = "1.0.0"
ORGANIZATION_NAME = "Value Investor Journal"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
IMPORTS_DIR = PROJECT_ROOT / "imports"
ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
DB_PATH = DATA_DIR / "dziennik.db"

DATE_FORMAT_ISO = "%Y-%m-%d"
DISPLAY_DATE_FORMAT = "dd.MM.yyyy"
REVIEW_INTERVAL_DAYS = 365

STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"

DEFAULT_CURRENCY = "USD"
SUPPORTED_CURRENCIES = ("USD", "EUR", "PLN", "GBP")

DEFAULT_SELL_THRESHOLD_GAIN = 0.20
DEFAULT_SELL_THRESHOLD_PROFIT = 0.10
DEFAULT_SELL_THRESHOLD_LOSS = -0.10

CATEGORY_RZUCAM = "RZUCAM SZTABKAMI"
CATEGORY_PROFIT = "ZAROBEK"
CATEGORY_NEUTRAL = "NEUTRALNY"
CATEGORY_NEGATIVE = "WYNIK NEGATYWNY"

INSTRUCTION_SELL = "SPRZEDAJ"
INSTRUCTION_HOLD = "TRZYMAJ"

CATEGORY_STYLES = {
    CATEGORY_RZUCAM: {"bg": "#4A4A2A", "fg": "#FFD700"},
    CATEGORY_PROFIT: {"bg": "#2A4A2A", "fg": "#90EE90"},
    CATEGORY_NEUTRAL: {"bg": "#2E2E2E", "fg": "#CCCCCC"},
    CATEGORY_NEGATIVE: {"bg": "#4A2A2A", "fg": "#FF6B6B"},
    STATUS_CLOSED: {"bg": "#3A3A3A", "fg": "#666666"},
}

METRIC_FIELDS = (
    "pe_ratio",
    "dividend_yield",
    "debt_to_equity",
    "roe",
    "payout_ratio",
    "revenue_growth_3y",
)

METRIC_LABELS = {
    "pe_ratio": "P/E ratio",
    "dividend_yield": "Dividend yield",
    "debt_to_equity": "D/E ratio",
    "roe": "ROE",
    "payout_ratio": "Payout ratio",
    "revenue_growth_3y": "Revenue growth 3Y",
}

METRIC_UNITS = {
    "pe_ratio": "",
    "dividend_yield": "%",
    "debt_to_equity": "",
    "roe": "%",
    "payout_ratio": "%",
    "revenue_growth_3y": "%",
}

ASSET_DEFAULTS = (
    ("Akcje", 0.60, "#3DAEE9", 1),
    ("Obligacje", 0.30, "#27AE60", 2),
    ("Złoto", 0.10, "#C9A227", 3),
)

UI = {
    "add_position": "+ Dodaj",
    "add_review": "Rewizja",
    "import_csv": "Import CSV",
    "export": "Eksport",
    "allocation": "Alokacja",
    "refresh": "Odśwież",
    "file": "Plik",
    "view": "Widok",
    "help": "Pomoc",
    "about": "O aplikacji",
}
