from src.database import (
    Database,
    init_db,
    seed_demo_data,
)


def test_database_seed_creates_demo_positions(tmp_path) -> None:

    db_path = tmp_path / "demo.db"

    init_db(db_path)

    seed_demo_data(db_path)

    db = Database(db_path)

    positions = db.get_all_positions(
        include_closed=True
    )

    assert {
        position.ticker
        for position in positions
    } == {
        "HEN",
        "DTG",
        "FME",
    }

    assert db.count_reviews() == 1

    assert len(
        db.get_all_asset_categories()
    ) == 3
