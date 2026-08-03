from src.metrics_engine import (
    MetricTrend,
    compare_metric,
)


def test_lower_is_better_metric_improves_when_lower() -> None:

    assert compare_metric(
        "pe_ratio",
        18.0,
        22.0,
    ) == MetricTrend.IMPROVED


def test_higher_is_better_metric_worsens_when_lower() -> None:

    assert compare_metric(
        "roe",
        10.0,
        12.0,
    ) == MetricTrend.WORSENED


def test_tolerance_returns_unchanged() -> None:

    assert compare_metric(
        "dividend_yield",
        3.05,
        3.0,
    ) == MetricTrend.UNCHANGED


def test_none_returns_unchanged() -> None:

    assert compare_metric(
        "debt_to_equity",
        None,
        0.2,
    ) == MetricTrend.UNCHANGED
