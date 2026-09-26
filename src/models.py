from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, NamedTuple

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
    """Pojedyncza decyzja inwestycyjna wraz z bieżącym stanem."""

    ticker: str
    isin: str
    name: str | None
    currency: str

    sector: str | None
    thesis: str | None
    initial_buy_price: float
    initial_buy_date: str

    quantity: int
    average_cost: float
    current_price: float | None

    sell_threshold_gain: float = DEFAULT_SELL_THRESHOLD_GAIN
    sell_threshold_profit: float = DEFAULT_SELL_THRESHOLD_PROFIT
    sell_threshold_loss: float = DEFAULT_SELL_THRESHOLD_LOSS

    status: str = STATUS_OPEN

    sell_date: str | None = None
    sell_price: float | None = None
    realized_gain: float | None = None
    review_date: str = ""

    id: int | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Position":
        current_price = _row_get(row, "current_price")

        return cls(
            id=_row_get(row, "id"),
            ticker=str(_row_get(row, "ticker", "")).upper(),
            isin=str(_row_get(row, "isin", "")),
            name=_row_get(row, "name"),
            currency=str(_row_get(row, "currency", DEFAULT_CURRENCY)),
            sector=_row_get(row, "sector"),
            thesis=_row_get(row, "thesis"),
            initial_buy_price=float(_row_get(row, "initial_buy_price", 0.0)),
            initial_buy_date=str(_row_get(row, "initial_buy_date", "")),
            sell_threshold_gain=float(
                _row_get(
                    row,
                    "sell_threshold_gain",
                    DEFAULT_SELL_THRESHOLD_GAIN,
                )
            ),
            sell_threshold_profit=float(
                _row_get(
                    row,
                    "sell_threshold_profit",
                    DEFAULT_SELL_THRESHOLD_PROFIT,
                )
            ),
            sell_threshold_loss=float(
                _row_get(
                    row,
                    "sell_threshold_loss",
                    DEFAULT_SELL_THRESHOLD_LOSS,
                )
            ),
            quantity=int(_row_get(row, "quantity", 0)),
            average_cost=float(_row_get(row, "average_cost", 0.0)),
            current_price=(None if current_price is None else float(current_price)),
            status=str(_row_get(row, "status", STATUS_OPEN)),
            sell_date=_row_get(row, "sell_date"),
            sell_price=_row_get(row, "sell_price"),
            realized_gain=_row_get(row, "realized_gain"),
            review_date=str(_row_get(row, "review_date", "")),
        )

    def to_db_tuple(self) -> tuple[Any, ...]:
        return (
            self.ticker.upper().strip(),
            self.isin.strip(),
            self.name.strip() if self.name else None,
            self.currency,
            self.sector,
            self.thesis,
            self.initial_buy_price,
            self.initial_buy_date,
            self.sell_threshold_gain,
            self.sell_threshold_profit,
            self.sell_threshold_loss,
            self.quantity,
            self.average_cost,
            self.current_price,
            self.status,
            self.sell_date,
            self.sell_price,
            self.realized_gain,
            self.review_date,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "isin": self.isin,
            "name": self.name,
            "currency": self.currency,
            "sector": self.sector,
            "thesis": self.thesis,
            "initial_buy_price": self.initial_buy_price,
            "initial_buy_date": self.initial_buy_date,
            "sell_threshold_gain": self.sell_threshold_gain,
            "sell_threshold_profit": self.sell_threshold_profit,
            "sell_threshold_loss": self.sell_threshold_loss,
            "quantity": self.quantity,
            "average_cost": self.average_cost,
            "current_price": self.current_price,
            "status": self.status,
            "sell_date": self.sell_date,
            "sell_price": self.sell_price,
            "realized_gain": self.realized_gain,
            "review_date": self.review_date,
        }


class PositionSnapshot(NamedTuple):
    """Niemutowalny snapshot ekonomiczny pozycji."""

    cost_basis: float
    market_value: float | None
    unrealized_gain: float | None
    unrealized_return: float | None
    thesis_return: float | None
    target_gain_price: float
    target_profit_price: float
    target_loss_price: float
    distance_to_gain_pct: float | None
    distance_to_loss_pct: float | None


class PositionValuation:
    """Czysta logika wyceny. Nie modyfikuje Position."""

    @staticmethod
    def snapshot(position: Position) -> PositionSnapshot:
        cost_basis = position.quantity * position.average_cost

        target_gain = position.average_cost * (1 + position.sell_threshold_gain)
        target_profit = position.average_cost * (1 + position.sell_threshold_profit)
        target_loss = position.average_cost * (1 + position.sell_threshold_loss)

        if position.current_price is None or position.quantity <= 0:
            return PositionSnapshot(
                cost_basis=cost_basis,
                market_value=None,
                unrealized_gain=None,
                unrealized_return=None,
                thesis_return=None,
                target_gain_price=target_gain,
                target_profit_price=target_profit,
                target_loss_price=target_loss,
                distance_to_gain_pct=None,
                distance_to_loss_pct=None,
            )

        market_value = position.quantity * position.current_price
        unrealized_gain = market_value - cost_basis

        unrealized_return = unrealized_gain / cost_basis if cost_basis != 0 else None

        thesis_return = (
            (position.current_price - position.initial_buy_price)
            / position.initial_buy_price
            if position.initial_buy_price != 0
            else None
        )

        distance_to_gain = (
            target_gain - position.current_price
        ) / position.current_price

        distance_to_loss = (
            position.current_price - target_loss
        ) / position.current_price

        return PositionSnapshot(
            cost_basis=cost_basis,
            market_value=market_value,
            unrealized_gain=unrealized_gain,
            unrealized_return=unrealized_return,
            thesis_return=thesis_return,
            target_gain_price=target_gain,
            target_profit_price=target_profit,
            target_loss_price=target_loss,
            distance_to_gain_pct=distance_to_gain,
            distance_to_loss_pct=distance_to_loss,
        )


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
        return (
            self.name,
            self.target_pct,
            self.actual_pct,
            self.color,
            self.sort_order,
        )

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
