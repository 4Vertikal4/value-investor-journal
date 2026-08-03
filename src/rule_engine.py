from __future__ import annotations

from src.config import (
    CATEGORY_NEGATIVE,
    CATEGORY_NEUTRAL,
    CATEGORY_PROFIT,
    CATEGORY_RZUCAM,
    DEFAULT_SELL_THRESHOLD_GAIN,
    DEFAULT_SELL_THRESHOLD_LOSS,
    DEFAULT_SELL_THRESHOLD_PROFIT,
    INSTRUCTION_HOLD,
    INSTRUCTION_SELL,
)


def calculate_return(buy_price: float, current_price: float) -> float:
    if buy_price <= 0:
        raise ValueError("Cena zakupu musi być większa od zera.")
    return round((current_price - buy_price) / buy_price, 4)


def categorize(return_pct: float) -> tuple[str, str]:
    return categorize_with_thresholds(
        return_pct=return_pct,
        gain_threshold=DEFAULT_SELL_THRESHOLD_GAIN,
        profit_threshold=DEFAULT_SELL_THRESHOLD_PROFIT,
        loss_threshold=DEFAULT_SELL_THRESHOLD_LOSS,
    )


def categorize_with_thresholds(
    return_pct: float,
    gain_threshold: float = DEFAULT_SELL_THRESHOLD_GAIN,
    profit_threshold: float = DEFAULT_SELL_THRESHOLD_PROFIT,
    loss_threshold: float = DEFAULT_SELL_THRESHOLD_LOSS,
) -> tuple[str, str]:
    if return_pct >= gain_threshold:
        return CATEGORY_RZUCAM, INSTRUCTION_SELL
    if return_pct >= profit_threshold:
        return CATEGORY_PROFIT, INSTRUCTION_HOLD
    if return_pct >= loss_threshold:
        return CATEGORY_NEUTRAL, INSTRUCTION_HOLD
    return CATEGORY_NEGATIVE, INSTRUCTION_SELL


def format_return(return_pct: float) -> str:
    return f"{return_pct * 100:.2f}%"
