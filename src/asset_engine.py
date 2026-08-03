from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from src.models import Position


def infer_asset_category(position: Position) -> str:
    sector = (position.sector or "").strip().lower()
    ticker = position.ticker.strip().upper()
    bond_words = ("oblig", "bond", "treasury", "skarb")
    gold_words = ("złoto", "zloto", "gold", "xau")
    cash_words = ("lokata", "gotówka", "gotowka", "cash", "deposit")

    if any(word in sector for word in bond_words) or ticker.endswith("BOND"):
        return "Obligacje"
    if any(word in sector for word in gold_words) or ticker in {
        "GLD",
        "IAU",
        "SGLN",
        "PHAU",
    }:
        return "Złoto"
    if any(word in sector for word in cash_words):
        return "Lokaty"
    return "Akcje"


def recalculate_actual_allocation(positions: Iterable[Position]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for position in positions:
        if position.status == "CLOSED":
            continue
        category = infer_asset_category(position)
        totals[category] += max(position.market_value(), 0.0)

    portfolio_total = sum(totals.values())
    if portfolio_total <= 0:
        return {category: 0.0 for category in totals}
    return {
        category: round(value / portfolio_total, 4)
        for category, value in totals.items()
    }


def get_rebalance_delta(
    target: dict[str, float], actual: dict[str, float]
) -> dict[str, float]:
    categories = set(target) | set(actual)
    return {
        category: round(target.get(category, 0.0) - actual.get(category, 0.0), 4)
        for category in categories
    }


def format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"
