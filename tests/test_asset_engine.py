from src.asset_engine import (
    get_rebalance_delta,
    recalculate_actual_allocation,
)

from src.models import Position


def test_recalculate_actual_allocation_groups_open_positions() -> None:

    positions = [
        Position(
            ticker="AAA",
            name="AAA",
            sector="Akcje",
            buy_price=100,
            current_price=100,
            buy_date="2024-01-01",
            review_date="2025-01-01",
        ),
        Position(
            ticker="GLD",
            name="Gold",
            sector="Złoto",
            buy_price=50,
            current_price=50,
            buy_date="2024-01-01",
            review_date="2025-01-01",
        ),
    ]

    actual = recalculate_actual_allocation(positions)

    assert actual["Akcje"] == 0.6667
    assert actual["Złoto"] == 0.3333


def test_rebalance_delta() -> None:

    assert get_rebalance_delta(
        {"Akcje": 0.6},
        {"Akcje": 0.5, "Złoto": 0.5},
    ) == {
        "Akcje": 0.1,
        "Złoto": -0.5,
    }
