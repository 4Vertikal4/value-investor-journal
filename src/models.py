from __future__ import annotations

import sqlite3

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# ============================================================
# POSITION STATUS
# ============================================================


class PositionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


# ============================================================
# REVIEW CATEGORY
# ============================================================


class ReviewCategory(StrEnum):
    BIG_WIN = "RZUCAM SZTABKAMI"
    PROFIT = "ZAROBEK"
    NEUTRAL = "NEUTRALNY"
    NEGATIVE = "WYNIK NEGATYWNY"


# ============================================================
# REVIEW INSTRUCTION
# ============================================================


class ReviewInstruction(StrEnum):
    HOLD = "TRZYMAJ"
    SELL = "SPRZEDAJ"


# ============================================================
# EVENT STATUS
# ============================================================


class EventStatus(StrEnum):
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"


# ============================================================
# EVENT TRIGGER TYPE
# ============================================================


class EventTriggerType(StrEnum):
    MANUAL = "MANUAL"
    PRICE_THRESHOLD = "PRICE_THRESHOLD"
    DATE = "DATE"
    FED_RATE = "FED_RATE"
    OIL_PRICE = "OIL_PRICE"
    CUSTOM = "CUSTOM"


# ============================================================
# POSITION
# ============================================================


@dataclass(slots=True)
class Position:
    id: int | None
    ticker: str
    name: str
    sector: str | None
    thesis: str | None

    quantity: float

    buy_price: float
    current_price: float | None

    buy_date: str
    review_date: str

    currency: str

    sell_threshold_gain: float
    sell_threshold_profit: float
    sell_threshold_loss: float

    status: PositionStatus = PositionStatus.OPEN

    @property
    def market_value(self) -> float:
        """
        Aktualna wartość pozycji.
        """
        if self.current_price is None:
            return self.buy_price * self.quantity

        return self.current_price * self.quantity

    @property
    def invested_value(self) -> float:
        """
        Wartość zainwestowana przy zakupie.
        """
        return self.buy_price * self.quantity

    @property
    def return_pct(self) -> float:
        """
        Zwrot procentowy pozycji.
        """
        if self.current_price is None:
            return 0.0

        return round(
            ((self.current_price - self.buy_price) / self.buy_price) * 100,
            4,
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Position":
        return cls(
            id=row["id"],
            ticker=row["ticker"],
            name=row["name"],
            sector=row["sector"],
            thesis=row["thesis"],
            quantity=row["quantity"],
            buy_price=row["buy_price"],
            current_price=row["current_price"],
            buy_date=row["buy_date"],
            review_date=row["review_date"],
            currency=row["currency"],
            sell_threshold_gain=row["sell_threshold_gain"],
            sell_threshold_profit=row["sell_threshold_profit"],
            sell_threshold_loss=row["sell_threshold_loss"],
            status=PositionStatus(row["status"]),
        )


# ============================================================
# REVIEW
# ============================================================


@dataclass(slots=True)
class Review:
    id: int | None
    position_id: int

    review_date: str

    price_then: float
    return_pct: float

    category: ReviewCategory
    instruction: ReviewInstruction

    notes: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Review":
        return cls(
            id=row["id"],
            position_id=row["position_id"],
            review_date=row["review_date"],
            price_then=row["price_then"],
            return_pct=row["return_pct"],
            category=ReviewCategory(row["category"]),
            instruction=ReviewInstruction(row["instruction"]),
            notes=row["notes"],
        )


# ============================================================
# ASSET CATEGORY
# ============================================================


@dataclass(slots=True)
class AssetCategory:
    id: int | None

    name: str

    target_pct: float
    actual_pct: float

    color: str

    icon_path: str | None

    sort_order: int = 0

    @property
    def delta_pct(self) -> float:
        """
        Różnica między target a actual.
        """
        return round(self.actual_pct - self.target_pct, 4)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AssetCategory":
        return cls(
            id=row["id"],
            name=row["name"],
            target_pct=row["target_pct"],
            actual_pct=row["actual_pct"],
            color=row["color"],
            icon_path=row["icon_path"],
            sort_order=row["sort_order"],
        )


# ============================================================
# EVENT
# ============================================================


@dataclass(slots=True)
class Event:
    id: int | None

    name: str
    description: str | None

    trigger_type: EventTriggerType
    trigger_condition: str

    action_message: str

    image_path: str | None

    status: EventStatus

    created_date: str | None
    triggered_date: str | None
    dismissed_date: str | None
    expires_date: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Event":
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            trigger_type=EventTriggerType(row["trigger_type"]),
            trigger_condition=row["trigger_condition"],
            action_message=row["action_message"],
            image_path=row["image_path"],
            status=EventStatus(row["status"]),
            created_date=row["created_date"],
            triggered_date=row["triggered_date"],
            dismissed_date=row["dismissed_date"],
            expires_date=row["expires_date"],
        )


# ============================================================
# EVENT LOG
# ============================================================


@dataclass(slots=True)
class EventLog:
    id: int | None

    event_id: int

    triggered_at: str

    user_action: str | None
    notes: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "EventLog":
        return cls(
            id=row["id"],
            event_id=row["event_id"],
            triggered_at=row["triggered_at"],
            user_action=row["user_action"],
            notes=row["notes"],
        )


# ============================================================
# MARKET DATA
# ============================================================


@dataclass(slots=True)
class MarketData:
    key: str

    value: float

    unit: str | None
    updated_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "MarketData":
        return cls(
            key=row["key"],
            value=row["value"],
            unit=row["unit"],
            updated_at=row["updated_at"],
        )


# ============================================================
# SQLITE HELPERS
# ============================================================


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """
    Zamienia sqlite3.Row na zwykły dict.
    """
    return {key: row[key] for key in row.keys()}
