from __future__ import annotations

import sqlite3
import shutil
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Sequence

from src.config import ASSET_DEFAULTS, DB_PATH, REVIEW_INTERVAL_DAYS, STATUS_CLOSED, STATUS_OPEN
from src.models import AssetCategory, MarketData, Position, Review

POSITIONS_SQL = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    sector TEXT,
    thesis TEXT,
    buy_price REAL NOT NULL,
    buy_date TEXT NOT NULL,
    review_date TEXT NOT NULL,
    currency TEXT DEFAULT 'USD',
    sell_threshold_gain REAL DEFAULT 0.20,
    sell_threshold_profit REAL DEFAULT 0.10,
    sell_threshold_loss REAL DEFAULT -0.10,
    status TEXT DEFAULT 'OPEN',
    current_price REAL
);
"""

REVIEWS_SQL = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    review_date TEXT DEFAULT CURRENT_DATE,
    price_then REAL NOT NULL,
    return_pct REAL NOT NULL,
    category TEXT NOT NULL,
    instruction TEXT NOT NULL,
    pe_ratio REAL,
    dividend_yield REAL,
    debt_to_equity REAL,
    roe REAL,
    payout_ratio REAL,
    revenue_growth_3y REAL,
    notes TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);
"""

ASSET_CATEGORIES_SQL = """
CREATE TABLE IF NOT EXISTS asset_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    target_pct REAL NOT NULL,
    actual_pct REAL DEFAULT 0.0,
    color TEXT DEFAULT '#3DAEE9',
    sort_order INTEGER DEFAULT 0
);
"""

MARKET_DATA_SQL = """
CREATE TABLE IF NOT EXISTS market_data (
    key TEXT PRIMARY KEY,
    value REAL NOT NULL,
    unit TEXT,
    updated_at TEXT
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(POSITIONS_SQL)
        conn.executescript(REVIEWS_SQL)
        conn.executescript(ASSET_CATEGORIES_SQL)
        conn.executescript(MARKET_DATA_SQL)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_position_date ON reviews(position_id, review_date DESC, id DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_status_review ON positions(status, review_date)")


class Database:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = get_connection(self.db_path)
        try:
            yield conn
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        init_db(self.db_path)

    def insert_position(self, position: Position) -> int:
        sql = """
        INSERT INTO positions (
            ticker, name, sector, thesis, buy_price, buy_date, review_date, currency,
            sell_threshold_gain, sell_threshold_profit, sell_threshold_loss, status, current_price
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.connection() as conn:
                cursor = conn.execute(sql, position.to_db_tuple())
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się dodać pozycji {position.ticker}: {exc}") from exc

    def get_position_by_id(self, position_id: int) -> Position | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,)).fetchone()
        return Position.from_row(row) if row else None

    def get_position_by_ticker(self, ticker: str) -> Position | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker.upper().strip(),)).fetchone()
        return Position.from_row(row) if row else None

    def get_all_positions(self, include_closed: bool = False) -> list[Position]:
        sql = "SELECT * FROM positions"
        params: tuple[object, ...] = ()
        if not include_closed:
            sql += " WHERE status != ?"
            params = (STATUS_CLOSED,)
        sql += " ORDER BY ticker COLLATE NOCASE"
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [Position.from_row(row) for row in rows]

    def update_position(self, position: Position) -> None:
        if position.id is None:
            raise ValueError("Pozycja musi mieć id przed aktualizacją.")
        sql = """
        UPDATE positions
        SET name = ?, sector = ?, thesis = ?, buy_price = ?, buy_date = ?, review_date = ?,
            currency = ?, sell_threshold_gain = ?, sell_threshold_profit = ?, sell_threshold_loss = ?,
            status = ?, current_price = ?
        WHERE id = ?
        """

        values = (
            position.name.strip(),
            position.sector,
            position.thesis,
            position.buy_price,
            position.buy_date,
            position.review_date,
            position.currency,
            position.sell_threshold_gain,
            position.sell_threshold_profit,
            position.sell_threshold_loss,
            position.status,
            position.current_price,
            position.id,
        )
        try:
            with self.connection() as conn:
                conn.execute(sql, values)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zaktualizować pozycji {position.ticker}: {exc}") from exc

    def update_position_current_price(self, position_id: int, current_price: float) -> None:
        try:
            with self.connection() as conn:
                conn.execute("UPDATE positions SET current_price = ? WHERE id = ?", (current_price, position_id))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zaktualizować aktualnej ceny: {exc}") from exc

    def update_position_after_review(self, position_id: int, current_price: float, next_review_date: str) -> None:
        try:
            with self.connection() as conn:
                conn.execute(
                    "UPDATE positions SET current_price = ?, review_date = ? WHERE id = ?",
                    (current_price, next_review_date, position_id),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zaktualizować pozycji po rewizji: {exc}") from exc

    def update_position_status(self, position_id: int, status: str) -> None:
        if status not in {STATUS_OPEN, STATUS_CLOSED}:
            raise ValueError("Status musi mieć wartość OPEN albo CLOSED.")
        try:
            with self.connection() as conn:
                conn.execute("UPDATE positions SET status = ? WHERE id = ?", (status, position_id))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zmienić statusu pozycji: {exc}") from exc

    def close_position(self, position_id: int) -> None:
        self.update_position_status(position_id, STATUS_CLOSED)

    def reopen_position(self, position_id: int) -> None:
        self.update_position_status(position_id, STATUS_OPEN)

    def delete_position(self, position_id: int) -> None:
        try:
            with self.connection() as conn:
                conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się usunąć pozycji: {exc}") from exc

    def insert_review(self, review: Review) -> int:
        sql = """
        INSERT INTO reviews (
            position_id, review_date, price_then, return_pct, category, instruction,
            pe_ratio, dividend_yield, debt_to_equity, roe, payout_ratio, revenue_growth_3y, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.connection() as conn:
                cursor = conn.execute(sql, review.to_db_tuple())
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zapisać rewizji: {exc}") from exc

    def get_reviews_for_position(self, position_id: int) -> list[Review]:
        sql = "SELECT * FROM reviews WHERE position_id = ? ORDER BY review_date DESC, id DESC"
        with self.connection() as conn:
            rows = conn.execute(sql, (position_id,)).fetchall()
        return [Review.from_row(row) for row in rows]

    def get_last_review_for_position(self, position_id: int) -> Review | None:
        sql = "SELECT * FROM reviews WHERE position_id = ? ORDER BY review_date DESC, id DESC LIMIT 1"
        with self.connection() as conn:
            row = conn.execute(sql, (position_id,)).fetchone()
        return Review.from_row(row) if row else None

    def get_previous_review_for_position(self, position_id: int, before_review_id: int | None = None) -> Review | None:
        if before_review_id is None:
            return self.get_last_review_for_position(position_id)
        sql = "SELECT * FROM reviews WHERE position_id = ? AND id < ? ORDER BY review_date DESC, id DESC LIMIT 1"
        with self.connection() as conn:
            row = conn.execute(sql, (position_id, before_review_id)).fetchone()
        return Review.from_row(row) if row else None

    def delete_review(self, review_id: int) -> None:
        try:
            with self.connection() as conn:
                conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się usunąć rewizji: {exc}") from exc

    def insert_asset_category(self, category: AssetCategory) -> int:
        sql = """
        INSERT INTO asset_categories (name, target_pct, actual_pct, color, sort_order)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self.connection() as conn:
                cursor = conn.execute(sql, category.to_db_tuple())
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się dodać kategorii assetów {category.name}: {exc}") from exc

    def get_all_asset_categories(self) -> list[AssetCategory]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM asset_categories ORDER BY sort_order, name COLLATE NOCASE").fetchall()
        return [AssetCategory.from_row(row) for row in rows]

    def get_asset_category_by_name(self, name: str) -> AssetCategory | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM asset_categories WHERE name = ?", (name,)).fetchone()
        return AssetCategory.from_row(row) if row else None

    def update_asset_category(self, category: AssetCategory) -> None:
        if category.id is None:
            raise ValueError("Kategoria musi mieć id przed aktualizacją.")
        sql = """
        UPDATE asset_categories
        SET name = ?, target_pct = ?, actual_pct = ?, color = ?, sort_order = ?
        WHERE id = ?
        """
        try:
            with self.connection() as conn:
                conn.execute(sql, (*category.to_db_tuple(), category.id))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zaktualizować kategorii assetów: {exc}") from exc

    def update_asset_category_actual(self, name: str, actual_pct: float) -> None:
        try:
            with self.connection() as conn:
                conn.execute("UPDATE asset_categories SET actual_pct = ? WHERE name = ?", (actual_pct, name))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zaktualizować aktualnej alokacji: {exc}") from exc

    def delete_asset_category(self, category_id: int) -> None:
        try:
            with self.connection() as conn:
                conn.execute("DELETE FROM asset_categories WHERE id = ?", (category_id,))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się usunąć kategorii assetów: {exc}") from exc

    def upsert_market_data(self, key: str, value: float, unit: str | None = None) -> None:
        updated_at = datetime.now().isoformat(timespec="seconds")
        sql = """
        INSERT INTO market_data (key, value, unit, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            unit = excluded.unit,
            updated_at = excluded.updated_at
        """
        try:
            with self.connection() as conn:
                conn.execute(sql, (key, value, unit, updated_at))
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zapisać danych rynkowych {key}: {exc}") from exc

    def get_market_data(self, key: str) -> MarketData | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM market_data WHERE key = ?", (key,)).fetchone()
        return MarketData.from_row(row) if row else None

    def get_all_market_data(self) -> list[MarketData]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM market_data ORDER BY key COLLATE NOCASE").fetchall()
        return [MarketData.from_row(row) for row in rows]

    def count_positions(self, include_closed: bool = True) -> int:
        sql = "SELECT COUNT(*) AS count FROM positions"
        params: tuple[object, ...] = ()
        if not include_closed:
            sql += " WHERE status != ?"
            params = (STATUS_CLOSED,)
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["count"] if row else 0)

    def count_reviews(self) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM reviews").fetchone()
        return int(row["count"] if row else 0)

    def is_database_empty(self) -> bool:
        return self.count_positions(include_closed=True) == 0

    def sum_portfolio_value(self, include_closed: bool = False) -> float:
        positions = self.get_all_positions(include_closed=include_closed)
        return round(sum(position.market_value() for position in positions if include_closed or position.status != STATUS_CLOSED), 2)

    def due_positions(self, on_date: date | None = None) -> list[Position]:
        on_date = on_date or date.today()
        rows: Sequence[sqlite3.Row]
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE status = ? AND review_date <= ? ORDER BY review_date, ticker COLLATE NOCASE",
                (STATUS_OPEN, on_date.isoformat()),

            return round(sum(position.market_value() for position in positions if include_closed or position.status != STATUS_CLOSED), 2)

    def export_database_backup(self, destination: Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, destination)
        return destination

    def seed_demo_data(db_path: Path = DB_PATH) -> None:
        db = Database(db_path)
        db.init()
        if not db.is_database_empty():
            return

        for name, target, color, order in ASSET_DEFAULTS:
            db.insert_asset_category(AssetCategory(name=name, target_pct=target, color=color, sort_order=order))

        today = date.today()
        buy_date = today - timedelta(days=220)
        next_review = buy_date + timedelta(days=REVIEW_INTERVAL_DAYS)

        positions = [
            Position(
                ticker="HEN",
                name="Heineken N.V.",
                sector="Akcje / Consumer Defensive",
                thesis="Demo: mocna marka globalna, stabilne przepływy i potencjał poprawy marży.",
                buy_price=82.00,
                current_price=96.50,
                buy_date=buy_date.isoformat(),
                review_date=next_review.isoformat(),
                currency="EUR",
            ),
            Position(
                ticker="DTG",
                name="Daimler Truck Holding AG",
                sector="Akcje / Industrials",
                thesis="Demo: ekspozycja na cykl ciężarówek, dyscyplina kosztowa i potencjał dywidendowy.",
                buy_price=34.20,
                current_price=31.80,
                buy_date=(buy_date - timedelta(days=30)).isoformat(),
                review_date=(next_review - timedelta(days=30)).isoformat(),
                currency="EUR",
            ),
            Position(
                ticker="FME",
                name="Fresenius Medical Care AG",
                sector="Akcje / Healthcare",
                thesis="Demo: restrukturyzacja, defensywny popyt i możliwy powrót ROE do średniej historycznej.",
                buy_price=42.50,
                current_price=47.20,
                buy_date=(buy_date - timedelta(days=60)).isoformat(),
                review_date=(next_review - timedelta(days=60)).isoformat(),
                currency="EUR",
            ),
        ]

        inserted: dict[str, int] = {}
        for position in positions:
            inserted[position.ticker] = db.insert_position(position)

        from src.rule_engine import calculate_return, categorize_with_thresholds

        hen_position = db.get_position_by_id(inserted["HEN"])
        if hen_position is not None:
            return_pct = calculate_return(hen_position.buy_price, 96.50)
            category, instruction = categorize_with_thresholds(
                return_pct,
                hen_position.sell_threshold_gain,
                hen_position.sell_threshold_profit,
                hen_position.sell_threshold_loss,
            )
            db.insert_review(
                Review(
                    position_id=hen_position.id or inserted["HEN"],
                    review_date=(today - timedelta(days=7)).isoformat(),
                    price_then=96.50,
                    return_pct=return_pct,
                    category=category,
                    instruction=instruction,
                    pe_ratio=18.5,
                    dividend_yield=2.15,
                    debt_to_equity=0.72,
                    roe=13.4,
                    payout_ratio=48.0,
                    revenue_growth_3y=4.2,
                    notes="Demo: pierwsza rewizja pokazująca metryki bazowe.",
                )
            )

    def insert_position(position: Position, db_path: Path = DB_PATH) -> int:
        return Database(db_path).insert_position(position)

    def get_all_positions(include_closed: bool = False, db_path: Path = DB_PATH) -> list[Position]:
        return Database(db_path).get_all_positions(include_closed=include_closed)

    def update_position(position: Position, db_path: Path = DB_PATH) -> None:
        Database(db_path).update_position(position)

    def delete_position(position_id: int, db_path: Path = DB_PATH) -> None:
        Database(db_path).delete_position(position_id)

    def insert_review(review: Review, db_path: Path = DB_PATH) -> int:
        return Database(db_path).insert_review(review)

    def get_reviews_for_position(position_id: int, db_path: Path = DB_PATH) -> list[Review]:
        return Database(db_path).get_reviews_for_position(position_id)

    def get_last_review_for_position(position_id: int, db_path: Path = DB_PATH) -> Review | None:
        return Database(db_path).get_last_review_for_position(position_id)

    def insert_asset_category(category: AssetCategory, db_path: Path = DB_PATH) -> int:
        return Database(db_path).insert_asset_category(category)

    def get_all_asset_categories(db_path: Path = DB_PATH) -> list[AssetCategory]:
        return Database(db_path).get_all_asset_categories()

    def update_asset_category(category: AssetCategory, db_path: Path = DB_PATH) -> None:
        Database(db_path).update_asset_category(category)

    def upsert_market_data(key: str, value: float, unit: str | None = None, db_path: Path = DB_PATH) -> None:
        Database(db_path).upsert_market_data(key, value, unit)

    def get_market_data(key: str, db_path: Path = DB_PATH) -> MarketData | None:
        return Database(db_path).get_market_data(key)