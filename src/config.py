from pathlib import Path

# ============================================================
# APP METADATA
# ============================================================

APP_NAME = "Value Investor Journal"
APP_VERSION = "0.1.0"
ORG_NAME = "4Vertikal4"

# ============================================================
# PATHS
# ============================================================

# src/ -> project root
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
IMPORTS_DIR = BASE_DIR / "imports"
ASSETS_DIR = BASE_DIR / "assets"

ICONS_DIR = ASSETS_DIR / "icons"
IMAGES_DIR = ASSETS_DIR / "images"
EVENT_IMAGES_DIR = IMAGES_DIR / "events"

DB_PATH = DATA_DIR / "dziennik.db"

# ============================================================
# DATABASE
# ============================================================

SQLITE_TIMEOUT = 30
SQLITE_JOURNAL_MODE = "WAL"

# ============================================================
# DEFAULT DECISION THRESHOLDS
# ============================================================

DEFAULT_SELL_THRESHOLD_GAIN = 0.20
DEFAULT_SELL_THRESHOLD_PROFIT = 0.10
DEFAULT_SELL_THRESHOLD_LOSS = -0.10

# ============================================================
# UI SETTINGS
# ============================================================

WINDOW_MIN_WIDTH = 1400
WINDOW_MIN_HEIGHT = 900

DEFAULT_FONT_FAMILY = "Noto Sans"
DEFAULT_FONT_SIZE = 10

# ============================================================
# DATE FORMATS
# ============================================================

DATE_FORMAT = "%Y-%m-%d"
DISPLAY_DATE_FORMAT = "dd.MM.yyyy"

# ============================================================
# CURRENCIES
# ============================================================

SUPPORTED_CURRENCIES = [
    "USD",
    "EUR",
    "PLN",
    "GBP",
]

DEFAULT_CURRENCY = "USD"

# ============================================================
# POSITION STATUS
# ============================================================

STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"

# ============================================================
# REVIEW CATEGORIES
# ============================================================

CATEGORY_BIG_WIN = "RZUCAM SZTABKAMI"
CATEGORY_PROFIT = "ZAROBEK"
CATEGORY_NEUTRAL = "NEUTRALNY"
CATEGORY_NEGATIVE = "WYNIK NEGATYWNY"

# ============================================================
# REVIEW INSTRUCTIONS
# ============================================================

INSTRUCTION_HOLD = "TRZYMAJ"
INSTRUCTION_SELL = "SPRZEDAJ"

# ============================================================
# EVENT STATUS
# ============================================================

EVENT_STATUS_ACTIVE = "ACTIVE"
EVENT_STATUS_TRIGGERED = "TRIGGERED"
EVENT_STATUS_DISMISSED = "DISMISSED"
EVENT_STATUS_EXPIRED = "EXPIRED"

# ============================================================
# EVENT TRIGGER TYPES
# ============================================================

EVENT_TRIGGER_MANUAL = "MANUAL"
EVENT_TRIGGER_PRICE_THRESHOLD = "PRICE_THRESHOLD"
EVENT_TRIGGER_DATE = "DATE"
EVENT_TRIGGER_FED_RATE = "FED_RATE"
EVENT_TRIGGER_OIL_PRICE = "OIL_PRICE"
EVENT_TRIGGER_CUSTOM = "CUSTOM"

# ============================================================
# COLOR PALETTE (BREEZE DARK + GRAND STRATEGY)
# ============================================================

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
    "event_bg": "#1E1E2E",
    "event_border": "#C9A227",
}

# ============================================================
# DASHBOARD CATEGORY COLORS
# ============================================================

CATEGORY_COLORS = {
    CATEGORY_BIG_WIN: {
        "bg": PALETTE["accent_gold"],
        "text": PALETTE["accent_gold_text"],
    },
    CATEGORY_PROFIT: {
        "bg": PALETTE["accent_green_bg"],
        "text": PALETTE["accent_green_text"],
    },
    CATEGORY_NEUTRAL: {
        "bg": PALETTE["accent_neutral_bg"],
        "text": PALETTE["accent_neutral_text"],
    },
    CATEGORY_NEGATIVE: {
        "bg": PALETTE["accent_red_bg"],
        "text": PALETTE["accent_red_text"],
    },
}

# ============================================================
# DEMO DATA
# ============================================================

ENABLE_DEMO_DATA = True

# ============================================================
# DIRECTORIES INIT
# ============================================================

REQUIRED_DIRS = [
    DATA_DIR,
    IMPORTS_DIR,
    ASSETS_DIR,
    ICONS_DIR,
    IMAGES_DIR,
    EVENT_IMAGES_DIR,
]


def ensure_directories() -> None:
    """
    Tworzy wymagane katalogi projektu jeśli nie istnieją.
    """
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
