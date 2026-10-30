from __future__ import annotations

import csv
from pathlib import Path

from src.database import Database
from src.importer_lightyear import import_lightyear_csv


CSV_COLUMNS = [
    "Side",
    "Trade date",
    "ISIN",
    "Ticker",
    "Instrument name",
    "Quantity",
    "Price",
    "Currency",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def buy(
    isin: str, ticker: str, quantity: str, price: str, trade_date: str
) -> dict[str, str]:
    return {
        "Side": "BUY",
        "Trade date": trade_date,
        "ISIN": isin,
        "Ticker": ticker,
        "Instrument name": f"Synthetic {ticker}",
        "Quantity": quantity,
        "Price": price,
        "Currency": "EUR",
    }


def sell(
    isin: str, ticker: str, quantity: str, price: str, trade_date: str
) -> dict[str, str]:
    row = buy(isin, ticker, quantity, price, trade_date)
    row["Side"] = "SELL"
    return row


def test_reimporting_identical_csv_does_not_change_positions(tmp_path) -> None:
    database = Database(tmp_path / "journal.db")
    database.init()
    csv_path = tmp_path / "lightyear.csv"
    rows = [
        buy("DE000DTR0CK8", "DTG", "13", "39.92", "2026-01-02"),
        buy("DE0005785802", "FME", "18", "40.31", "2026-01-02"),
        buy("DE0006048408", "HEN", "8", "62.45", "2026-01-02"),
        buy("NL0009432491", "VPK", "5", "47.40", "2026-01-02"),
    ]
    write_csv(csv_path, rows)

    first = import_lightyear_csv(csv_path, database)
    assert first.inserted == 4
    expected_quantities = {"DTG": 13, "FME": 18, "HEN": 8, "VPK": 5}
    assert (
        {p.ticker: p.quantity for p in database.get_all_positions()}
        == expected_quantities
    )

    database.update_position_current_price(
        next(p.id for p in database.get_all_positions() if p.ticker == "HEN"), 71.4
    )
    before = {p.ticker: p.to_dict() for p in database.get_all_positions()}

    reopened_database = Database(tmp_path / "journal.db")
    duplicate = import_lightyear_csv(csv_path, reopened_database)
    assert duplicate.already_imported is True
    assert {p.ticker: p.to_dict() for p in reopened_database.get_all_positions()} == before

    same_content_different_name = tmp_path / "renamed.csv"
    same_content_different_name.write_bytes(csv_path.read_bytes())
    duplicate_renamed = import_lightyear_csv(
        same_content_different_name, reopened_database
    )
    assert duplicate_renamed.already_imported is True
    assert (
        {p.ticker: p.to_dict() for p in reopened_database.get_all_positions()}
        == before
    )


def test_changed_content_with_same_filename_is_imported(tmp_path) -> None:
    database = Database(tmp_path / "journal.db")
    database.init()
    csv_path = tmp_path / "lightyear.csv"

    write_csv(
        csv_path,
        [buy("DE000DTR0CK8", "DTG", "13", "39.92", "2026-01-02")],
    )
    first = import_lightyear_csv(csv_path, database)
    assert first.already_imported is False

    write_csv(
        csv_path,
        [buy("DE000DTR0CK8", "DTG", "2", "42.00", "2026-02-02")],
    )
    changed = import_lightyear_csv(csv_path, database)
    assert changed.already_imported is False
    position = database.get_position_by_isin("DE000DTR0CK8")
    assert position is not None
    assert position.quantity == 15
    assert position.average_cost == (13 * 39.92 + 2 * 42.0) / 15


def test_buy_and_partial_and_full_sell_rules_are_preserved(tmp_path) -> None:
    database = Database(tmp_path / "journal.db")
    database.init()
    first_csv = tmp_path / "trades.csv"
    write_csv(
        first_csv,
        [
            buy("DE000DTR0CK8", "DTG", "2", "10", "2026-01-01"),
            buy("DE000DTR0CK8", "DTG", "1", "14", "2026-01-02"),
            sell("DE000DTR0CK8", "DTG", "1", "12", "2026-01-03"),
        ],
    )

    import_lightyear_csv(first_csv, database)
    position = database.get_position_by_isin("DE000DTR0CK8")
    assert position is not None
    assert position.quantity == 2
    assert position.average_cost == (2 * 10 + 14) / 3
    assert position.status == "OPEN"

    close_csv = tmp_path / "close.csv"
    write_csv(
        close_csv,
        [sell("DE000DTR0CK8", "DTG", "2", "15", "2026-01-04")],
    )
    import_lightyear_csv(close_csv, database)
    closed = database.get_position_by_isin("DE000DTR0CK8")
    assert closed is not None
    assert closed.quantity == 0
    assert closed.status == "CLOSED"
    assert closed.sell_date == "2026-01-04"

    duplicate_close = import_lightyear_csv(close_csv, database)
    assert duplicate_close.already_imported is True
    unchanged = database.get_position_by_isin("DE000DTR0CK8")
    assert unchanged is not None
    assert unchanged.to_dict() == closed.to_dict()


def test_existing_position_survives_additive_import_table_creation(tmp_path) -> None:
    database_path = tmp_path / "journal.db"
    database = Database(database_path)
    database.init()
    csv_path = tmp_path / "lightyear.csv"
    write_csv(
        csv_path,
        [buy("DE000DTR0CK8", "DTG", "13", "39.92", "2026-01-02")],
    )
    import_lightyear_csv(csv_path, database)
    before = database.get_position_by_isin("DE000DTR0CK8")
    assert before is not None

    with database.connection() as connection:
        connection.execute("DROP TABLE lightyear_imports")
    database.init()

    after = database.get_position_by_isin("DE000DTR0CK8")
    assert after is not None
    assert after.to_dict() == before.to_dict()
    with database.connection() as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'lightyear_imports'"
        ).fetchone()
    assert table is not None
