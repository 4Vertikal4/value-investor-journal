from __future__ import annotations

from enum import Enum


class MetricTrend(Enum):
    IMPROVED = "improved"
    WORSENED = "worsened"
    UNCHANGED = "unchanged"


METRIC_DIRECTION = {
    "pe_ratio": "lower_is_better",
    "dividend_yield": "higher_is_better",
    "debt_to_equity": "lower_is_better",
    "roe": "higher_is_better",
    "payout_ratio": "lower_is_better",
    "revenue_growth_3y": "higher_is_better",
}


def compare_metric(
    metric_name: str, current: float | None, previous: float | None
) -> MetricTrend:
    if current is None or previous is None:
        return MetricTrend.UNCHANGED
    if previous == 0:
        if current == 0:
            return MetricTrend.UNCHANGED
        direction = METRIC_DIRECTION.get(metric_name, "lower_is_better")
        if direction == "lower_is_better":
            return MetricTrend.WORSENED if current > previous else MetricTrend.IMPROVED
        return MetricTrend.IMPROVED if current > previous else MetricTrend.WORSENED

    diff_pct = abs((current - previous) / previous)
    if diff_pct <= 0.05:
        return MetricTrend.UNCHANGED

    direction = METRIC_DIRECTION.get(metric_name, "lower_is_better")
    if direction == "lower_is_better":
        return MetricTrend.IMPROVED if current < previous else MetricTrend.WORSENED
    return MetricTrend.IMPROVED if current > previous else MetricTrend.WORSENED


def get_trend_color(trend: MetricTrend) -> tuple[str, str]:
    if trend == MetricTrend.IMPROVED:
        return "#90EE90", "🟢"
    if trend == MetricTrend.WORSENED:
        return "#FF6B6B", "🔴"
    return "#888888", "⚪"


def trend_label(trend: MetricTrend) -> str:
    if trend == MetricTrend.IMPROVED:
        return "polepszyło się"
    if trend == MetricTrend.WORSENED:
        return "pogorszyło się"
    return "bez zmian"


def describe_metric_change(
    metric_name: str, current: float | None, previous: float | None
) -> str:
    trend = compare_metric(metric_name, current, previous)
    if trend == MetricTrend.UNCHANGED:
        return "bez zmian"

    direction = METRIC_DIRECTION.get(metric_name, "lower_is_better")
    went_up = current is not None and previous is not None and current > previous

    if metric_name == "pe_ratio":
        return "taniej" if trend == MetricTrend.IMPROVED else "drożej"
    if metric_name == "debt_to_equity":
        return "mniej długu" if trend == MetricTrend.IMPROVED else "więcej długu"
    if metric_name == "payout_ratio":
        return "bezpieczniej" if trend == MetricTrend.IMPROVED else "więcej wypłacane"
    if direction == "higher_is_better":
        return "więcej" if went_up else "mniej"
    return "niżej" if not went_up else "wyżej"


def summarize_trends(trends: dict[str, MetricTrend]) -> dict[MetricTrend, int]:
    return {
        MetricTrend.IMPROVED: sum(
            1 for trend in trends.values() if trend == MetricTrend.IMPROVED
        ),
        MetricTrend.WORSENED: sum(
            1 for trend in trends.values() if trend == MetricTrend.WORSENED
        ),
        MetricTrend.UNCHANGED: sum(
            1 for trend in trends.values() if trend == MetricTrend.UNCHANGED
        ),
    }
