
from __future__ import annotations

from enum import Enum
import json
from datetime import date
from src.fundamentals import series_signature


class MetricTrend(Enum):
    IMPROVED = "improved"
    WORSENED = "worsened"
    UNCHANGED = "unchanged"
    NO_DATA = "no_data"


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
        return MetricTrend.NO_DATA
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
    if trend == MetricTrend.NO_DATA:
        return "brak porównania"
    if trend == MetricTrend.IMPROVED:
        return "polepszyło się"
    if trend == MetricTrend.WORSENED:
        return "pogorszyło się"
    return "bez zmian"


def describe_metric_change(
    metric_name: str, current: float | None, previous: float | None
) -> str:
    trend = compare_metric(metric_name, current, previous)
    if trend == MetricTrend.NO_DATA:
        return "brak porównania"
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
        MetricTrend.NO_DATA: sum(trend == MetricTrend.NO_DATA for trend in trends.values()),
    }


def fundamental_change(current: dict, previous: dict | None) -> str:
    """Neutral period comparison; never labels a ratio movement an investment decision."""
    if previous is None:
        return "brak porównania"
    a, b = current["observation"], previous["observation"]
    comparable = all(a[k] == b[k] for k in ("metric", "scope", "isin", "definition", "unit", "currency"))
    comparable = comparable and current["issuer"]["id"] == previous["issuer"]["id"]
    comparable = comparable and a["period"]["basis"] == b["period"]["basis"]
    comparable = comparable and a["period"]["end"] != b["period"]["end"]
    if comparable and a["period"]["basis"] != "instant":
        a_days = (date.fromisoformat(a["period"]["end"]) - date.fromisoformat(a["period"]["start"])).days
        b_days = (date.fromisoformat(b["period"]["end"]) - date.fromisoformat(b["period"]["start"])).days
        tolerance = 21 if a["period"]["basis"] == "quarter" else 45
        comparable = abs(a_days - b_days) <= tolerance
    if not comparable or a["value"] is None or b["value"] is None:
        return "brak porównania (brak danych lub inna definicja/okres/jednostka)"
    delta = a["value"] - b["value"]
    unit = "p.p." if a["unit"] == "percent" else a["currency"] or "×"
    return f"{'wzrost' if delta > 0 else 'spadek' if delta < 0 else 'bez zmian'}: {delta:+.6g} {unit}"


def review_metric_source(review, metric: str) -> dict | None:
    if review is None or not review.fundamental_evidence_json:
        return None
    evidence = json.loads(review.fundamental_evidence_json)
    entry = evidence["metric_inputs"][metric]
    if entry["origin"] != "imported":
        return None
    return next((r for r in evidence["observations"] if r["id"] == entry["observation_id"]), None)


def sources_comparable(current: dict | None, previous: dict | None) -> bool:
    # Preserve manual/legacy comparisons, explicitly labelled as unverified in UI.
    if current is None and previous is None:
        return True
    return bool(current and previous and series_signature(current) == series_signature(previous))

