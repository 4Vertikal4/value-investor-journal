from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.config import (
    DEFAULT_CURRENCY,
    DEFAULT_SELL_THRESHOLD_GAIN,
    DEFAULT_SELL_THRESHOLD_LOSS,
    DEFAULT_SELL_THRESHOLD_PROFIT,
    STATUS_OPEN,
)


def _row_get(row: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


@dataclass(slots=True)
class Position:
    ticker: str
    name: str
    buy_price: float
    buy_date: str
    review_date: str
    sector: str | None = None
    thesis: str | None = None
    currency: str = DEFAULT_CURRENCY
    sell_threshold_gain: float = DEFAULT_SELL_THRESHOLD_GAIN
    sell_threshold_profit: float = DEFAULT_SELL_THRESHOLD_PROFIT
    sell_threshold_loss: float = DEFAULT_SELL_THRESHOLD_LOSS
    status: str = STATUS_OPEN
    current_price: float | None = None
    id: int | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Position":
        return cls(
            id=_row_get(row, "id"),
            ticker=str(_row_get(row, "ticker", "")).upper(),
            name=str(_row_get(row, "name", "")),
            sector=_row_get(row, "sector"),
            thesis=_row_get(row, "thesis"),
            buy_price=float(_row_get(row, "buy_price", 0.0)),
            buy_date=str(_row_get(row, "buy_date", "")),
            review_date=str(_row_get(row, "review_date", "")),
            currency=str(_row_get(row, "currency", DEFAULT_CURRENCY)),
            sell_threshold_gain=float(_row_get(row, "sell_threshold_gain", DEFAULT_SELL_THRESHOLD_GAIN)),
            sell_threshold_profit=float(_row_get(row, "sell_threshold_profit", DEFAULT_SELL_THRESHOLD_PROFIT)),
            sell_threshold_loss=float(_row_get(row, "sell_threshold_loss", DEFAULT_SELL_THRESHOLD_LOSS)),
            status=str(_row_get(row, "status", STATUS_OPEN)),
            current_price=(
                None
                if _row_get(row, "current_price") is None
                else float(_row_get(row, "current_price"))
            ),
        )

    def display_price(self) -> float:
        return self.current_price if self.current_price is not None else self.buy_price

    def market_value(self) -> float:
        return self.display_price()

    def to_db_tuple(self) -> tuple[Any, ...]:
        return (
            self.ticker.upper().strip(),
            self.name.strip(),
            self.sector,
            self.thesis,
            self.buy_price,
            self.buy_date,
            self.review_date,
            self.currency,
            self.sell_threshold_gain,
            self.sell_threshold_profit,
            self.sell_threshold_loss,
            self.status,
            self.current_price,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "thesis": self.thesis,
            "buy_price": self.buy_price,
            "buy_date": self.buy_date,
            "review_date": self.review_date,
            "currency": self.currency,
            "sell_threshold_gain": self.sell_threshold_gain,
            "sell_threshold_profit": self.sell_threshold_profit,
            "sell_threshold_loss": self.sell_threshold_loss,
            "status": self.status,
            "current_price": self.current_price,
        }


@dataclass(slots=True)
class Review:
    position_id: int
    review_date: str
    price_then: float
    return_pct: float
    category: str
    instruction: str
    @dataclass(slots=True)
class Review:
    position_id: int
    review_date: str
    price_then: float
    return_pct: float
    category: str
    instruction: str
    pe_ratio: float | None = None
    dividend_yield: float | None = None
    debt_to_equity: float | None = None
    roe: float | None = None
    payout_ratio: float | None = None
    revenue_growth_3y: float | None = None
    notes: str | None = None
    id: int | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Review":
        return cls(
            id=_row_get(row, "id"),
            position_id=int(_row_get(row, "position_id")),
            review_date=str(_row_get(row, "review_date", "")),
            price_then=float(_row_get(row, "price_then", 0.0)),
            return_pct=float(_row_get(row, "return_pct", 0.0)),
            category=str(_row_get(row, "category", "")),
            instruction=str(_row_get(row, "instruction", "")),
            pe_ratio=_row_get(row, "pe_ratio"),
            dividend_yield=_row_get(row, "dividend_yield"),
            debt_to_equity=_row_get(row, "debt_to_equity"),
            roe=_row_get(row, "roe"),
            payout_ratio=_row_get(row, "payout_ratio"),
            revenue_growth_3y=_row_get(row, "revenue_growth_3y"),
            notes=_row_get(row, "notes"),
        )

    def metric_value(self, metric_name: str) -> float | None:
        value = getattr(self, metric_name, None)
        return None if value is None else float(value)

    def to_db_tuple(self) -> tuple[Any, ...]:
        return (
            self.position_id,
            self.review_date,
            self.price_then,
            self.return_pct,
            self.category,
            self.instruction,
            self.pe_ratio,
            self.dividend_yield,
            self.debt_to_equity,
            self.roe,
            self.payout_ratio,
            self.revenue_growth_3y,
            self.notes,
        )

        def to_dict(self) -> dict[str, Any]:
            return {
                "id": self.id,
                "position_id": self.position_id,
                "review_date": self.review_date,
                "price_then": self.price_then,
                "return_pct": self.return_pct,
                "category": self.category,
                "instruction": self.instruction,
                "pe_ratio": self.pe_ratio,
                "dividend_yield": self.dividend_yield,
                "debt_to_equity": self.debt_to_equity,
                "roe": self.roe,
                "payout_ratio": self.payout_ratio,
                "revenue_growth_3y": self.revenue_growth_3y,
                "notes": self.notes,
            }


@dataclass(slots=True)
class AssetCategory:
    name: str
    target_pct: float
    actual_pct: float = 0.0
    color: str = "#3DAEE9"
    sort_order: int = 0
    id: int | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "AssetCategory":
        return cls(
            id=_row_get(row, "id"),
            name=str(_row_get(row, "name", "")),
            target_pct=float(_row_get(row, "target_pct", 0.0)),
            actual_pct=float(_row_get(row, "actual_pct", 0.0)),
            color=str(_row_get(row, "color", "#3DAEE9")),
            sort_order=int(_row_get(row, "sort_order", 0)),
        )

    def to_db_tuple(self) -> tuple[Any, ...]:
        return (self.name, self.target_pct, self.actual_pct, self.color, self.sort_order)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "target_pct": self.target_pct,
            "actual_pct": self.actual_pct,
            "color": self.color,
            "sort_order": self.sort_order,
        }


@dataclass(slots=True)
class MarketData:
    key: str
    value: float
    unit: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "MarketData":
        return cls(
            key=str(_row_get(row, "key", "")),
            value=float(_row_get(row, "value", 0.0)),
            unit=_row_get(row, "unit"),
            updated_at=_row_get(row, "updated_at"),
        )