from src.rule_engine import (
    calculate_return,
    categorize,
)


def test_calculate_return_rounds_to_four_places() -> None:

    assert calculate_return(
        100,
        112.345,
    ) == 0.1234


def test_categorize_thresholds() -> None:

    assert categorize(
        0.20
    ) == (
        "RZUCAM SZTABKAMI",
        "SPRZEDAJ",
    )

    assert categorize(
        0.10
    ) == (
        "ZAROBEK",
        "TRZYMAJ",
    )

    assert categorize(
        -0.10
    ) == (
        "NEUTRALNY",
        "TRZYMAJ",
    )

    assert categorize(
        -0.1001
    ) == (
        "WYNIK NEGATYWNY",
        "SPRZEDAJ",
    )
