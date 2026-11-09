

from __future__ import annotations

import sqlite3
import shutil
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Sequence

from src.config import (
    ASSET_DEFAULTS,
    DB_PATH,
    REVIEW_INTERVAL_DAYS,
    STATUS_CLOSED,
    STATUS_OPEN,
)
from src.models import AssetCategory, MarketData, Position, PositionValuation, Review
from src.fundamentals import FundamentalStore, migrate_fundamentals

POSITIONS_SQL = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    isin TEXT NOT NULL UNIQUE,
    name TEXT,
    sector TEXT,
    thesis TEXT,
    currency TEXT NOT NULL DEFAULT 'USD',
    initial_buy_price REAL NOT NULL,
    initial_buy_date TEXT NOT NULL,
    sell_threshold_gain REAL DEFAULT 0.20,
    sell_threshold_profit REAL DEFAULT 0.10,
    sell_threshold_loss REAL DEFAULT -0.10,
    quantity INTEGER NOT NULL,
    average_cost REAL NOT NULL,
    current_price REAL,
    status TEXT DEFAULT 'OPEN',
    sell_date TEXT,
    sell_price REAL,
    realized_gain REAL,
    review_date TEXT NOT NULL
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

LIGHTYEAR_IMPORTS_SQL = """
CREATE TABLE IF NOT EXISTS lightyear_imports (
    content_sha256 TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        _migrate_positions_schema(conn)
        conn.executescript(REVIEWS_SQL)
        conn.executescript(ASSET_CATEGORIES_SQL)
        conn.executescript(MARKET_DATA_SQL)
        conn.executescript(LIGHTYEAR_IMPORTS_SQL)
        migrate_fundamentals(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reviews_position_date ON reviews(position_id, review_date DESC, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_status_review ON positions(status, review_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_isin ON positions(isin)"
        )
        category_count = conn.execute(
            "SELECT COUNT(*) AS count FROM asset_categories"
        ).fetchone()
        if category_count is not None and int(category_count["count"]) == 0:
            conn.executemany(
                """
                INSERT INTO asset_categories (
                    name, target_pct, actual_pct, color, sort_order
                ) VALUES (?, ?, 0.0, ?, ?)
                """,
                ASSET_DEFAULTS,
            )


def _migrate_positions_schema(conn: sqlite3.Connection) -> None:
    """Add fields introduced by the Position migration to an existing database.

    SQLite does not update an existing table when CREATE TABLE IF NOT EXISTS is
    executed.  The migration is intentionally additive so it does not destroy a
    user's journal.  Legacy buy_price/buy_date values are copied when present.
    """
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(positions)").fetchall()
    }
    additions = {
        "isin": "TEXT NOT NULL DEFAULT ''",
        "name": "TEXT",
        "currency": "TEXT NOT NULL DEFAULT 'USD'",
        "sector": "TEXT",
        "thesis": "TEXT",
        "initial_buy_price": "REAL NOT NULL DEFAULT 0",
        "initial_buy_date": "TEXT NOT NULL DEFAULT ''",
        "sell_threshold_gain": "REAL NOT NULL DEFAULT 0.20",
        "sell_threshold_profit": "REAL NOT NULL DEFAULT 0.10",
        "sell_threshold_loss": "REAL NOT NULL DEFAULT -0.10",
        "quantity": "INTEGER NOT NULL DEFAULT 1",
        "average_cost": "REAL NOT NULL DEFAULT 0",
        "current_price": "REAL",
        "status": "TEXT NOT NULL DEFAULT 'OPEN'",
        "sell_date": "TEXT",
        "sell_price": "REAL",
        "realized_gain": "REAL",
        "review_date": "TEXT NOT NULL DEFAULT ''",
    }
    for column, definition in additions.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE positions ADD COLUMN {column} {definition}")

    if "buy_price" in columns:
        conn.execute(
            """
            UPDATE positions
            SET initial_buy_price = buy_price
            WHERE initial_buy_price = 0
            """
        )
    if "buy_date" in columns:
        conn.execute(
            """
            UPDATE positions
            SET initial_buy_date = buy_date
            WHERE initial_buy_date = ''
            """
        )
    conn.execute(
        """
        UPDATE positions
        SET average_cost = initial_buy_price
        WHERE average_cost = 0 AND initial_buy_price > 0
        """
    )


class Database:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.fundamentals = FundamentalStore(self)

    @contextmanager
    def connection(
        self, existing_connection: sqlite3.Connection | None = None
    ) -> Iterator[sqlite3.Connection]:
        owns_connection = existing_connection is None
        conn = (
            existing_connection
            if existing_connection is not None
            else get_connection(self.db_path)
        )
        try:
            yield conn
            if owns_connection:
                conn.commit()
        except Exception:
            if owns_connection:
                conn.rollback()
            raise
        finally:
            if owns_connection:
                conn.close()

    def init(self) -> None:
        init_db(self.db_path)

    @contextmanager
    def lightyear_import_transaction(
        self, content_sha256: str, file_name: str
    ) -> Iterator[tuple[sqlite3.Connection, bool]]:
        """Apply one CSV and its content receipt in the same SQLite transaction."""
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            imported = conn.execute(
                "SELECT 1 FROM lightyear_imports WHERE content_sha256 = ?",
                (content_sha256,),
            ).fetchone()
            already_imported = imported is not None
            yield conn, already_imported
            if not already_imported:
                conn.execute(
                    "INSERT INTO lightyear_imports (content_sha256, file_name) "
                    "VALUES (?, ?)",
                    (content_sha256, file_name),
                )

    def insert_position(
        self,
        position: Position,
        *,
        _connection: sqlite3.Connection | None = None,
    ) -> int:
        position.validate()
        sql = """
        INSERT INTO positions (
            ticker,
            isin,
            name,
            currency,
            sector,
            thesis,
            initial_buy_price,
            initial_buy_date,
            sell_threshold_gain,
            sell_threshold_profit,
            sell_threshold_loss,
            quantity,
            average_cost,
            current_price,
            status,
            sell_date,
            sell_price,
            realized_gain,
            review_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.connection(_connection) as conn:
                cursor = conn.execute(sql, position.to_db_tuple())
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Nie udało się dodać pozycji {position.ticker}: {exc}"
            ) from exc

    def get_position_by_id(self, position_id: int) -> Position | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM positions WHERE id = ?", (position_id,)
            ).fetchone()
        return Position.from_row(row) if row else None

    def get_position_by_ticker(self, ticker: str) -> Position | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM positions WHERE ticker = ?", (ticker.upper().strip(),)
            ).fetchone()
        return Position.from_row(row) if row else None

    def get_position_by_isin(
        self, isin: str, *, _connection: sqlite3.Connection | None = None
    ) -> Position | None:
        normalized_isin = isin.upper().strip()
        if not normalized_isin:
            return None
        with self.connection(_connection) as conn:
            row = conn.execute(
                "SELECT * FROM positions WHERE UPPER(isin) = ? ORDER BY id LIMIT 1",
                (normalized_isin,),
            ).fetchone()
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

    def update_position(
        self,
        position: Position,
        *,
        _connection: sqlite3.Connection | None = None,
    ) -> None:
        if position.id is None:
            raise ValueError("Pozycja musi mieć id przed aktualizacją.")

        position.validate()

        sql = """
        UPDATE positions
        SET ticker = ?,
            isin = ?,
            name = ?,
            currency = ?,
            sector = ?,
            thesis = ?,
            initial_buy_price = ?,
            initial_buy_date = ?,
            sell_threshold_gain = ?,
            sell_threshold_profit = ?,
            sell_threshold_loss = ?,
            quantity = ?,
            average_cost = ?,
            current_price = ?,
            status = ?,
            sell_date = ?,
            sell_price = ?,
            realized_gain = ?,
            review_date = ?
        WHERE id = ?
        """

        try:
            with self.connection(_connection) as conn:
                stored = conn.execute(
                    """
                    SELECT isin, initial_buy_price, initial_buy_date
                    FROM positions
                    WHERE id = ?
                    """,
                    (position.id,),
                ).fetchone()
                if stored is None:
                    raise ValueError(f"Nie znaleziono pozycji o id {position.id}.")

                stored_isin = str(stored["isin"] or "").upper().strip()
                new_isin = position.isin.upper().strip()
                if stored_isin and stored_isin != new_isin:
                    raise ValueError("ISIN istniejącej pozycji nie może być zmieniony.")
                if (
                    float(stored["initial_buy_price"])
                    != position.initial_buy_price
                    or str(stored["initial_buy_date"]) != position.initial_buy_date
                ):
                    raise ValueError(
                        "Pierwotna cena i data zakupu nie mogą być zmienione."
                    )

                cursor = conn.execute(sql, (*position.to_db_tuple(), position.id))
                if cursor.rowcount != 1:
                    raise RuntimeError("Aktualizacja pozycji nie zmieniła żadnego rekordu.")
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Nie udało się zaktualizować pozycji {position.ticker}: {exc}"
            ) from exc

    def update_position_current_price(
        self, position_id: int, current_price: float | None
    ) -> None:
        if current_price is not None and current_price <= 0:
            raise ValueError("Aktualna cena musi być większa od zera.")
        try:
            with self.connection() as conn:
                conn.execute(
                    "UPDATE positions SET current_price = ? WHERE id = ?",
                    (current_price, position_id),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Nie udało się zaktualizować aktualnej ceny: {exc}"
            ) from exc

    def update_position_after_review(
        self, position_id: int, current_price: float, next_review_date: str
    ) -> None:
        if current_price <= 0:
            raise ValueError("Aktualna cena musi być większa od zera.")
        try:
            with self.connection() as conn:
                conn.execute(
                    "UPDATE positions SET current_price = ?, review_date = ? WHERE id = ?",
                    (current_price, next_review_date, position_id),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Nie udało się zaktualizować pozycji po rewizji: {exc}"
            ) from exc

    def update_position_status(self, position_id: int, status: str) -> None:
        if status not in {STATUS_OPEN, STATUS_CLOSED}:
            raise ValueError("Status musi mieć wartość OPEN albo CLOSED.")
        raise RuntimeError(
            "Nie zmieniaj samego statusu. Użyj close_position() albo "
            "reopen_position(), aby zachować spójność danych."
        )

    def close_position(
        self,
        position_id: int,
        sell_price: float,
        sell_date: str,
        *,
        _connection: sqlite3.Connection | None = None,
    ) -> None:
        """Close a position in one transaction and store the realized return."""
        if sell_price <= 0:
            raise ValueError("Cena sprzedaży musi być większa od zera.")
        try:
            date.fromisoformat(sell_date)
        except ValueError as exc:
            raise ValueError("Data sprzedaży musi mieć format RRRR-MM-DD.") from exc

        try:
            with self.connection(_connection) as conn:
                if not conn.in_transaction:
                    conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT * FROM positions WHERE id = ?",
                    (position_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"Nie znaleziono pozycji o id {position_id}.")
                position = Position.from_row(row)
                if position.status == STATUS_CLOSED:
                    raise ValueError("Pozycja jest już zamknięta.")
                if position.quantity <= 0:
                    raise ValueError("Nie można zamknąć pozycji bez posiadanych akcji.")
                realized_gain = PositionValuation.realized_return(
                    position, sell_price
                )
                conn.execute(
                    """
                    UPDATE positions
                    SET quantity = 0,
                        status = ?,
                        sell_date = ?,
                        sell_price = ?,
                        realized_gain = ?
                    WHERE id = ?
                    """,
                    (
                        STATUS_CLOSED,
                        sell_date,
                        sell_price,
                        realized_gain,
                        position_id,
                    ),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zamknąć pozycji: {exc}") from exc

    def reopen_position(
        self,
        position_id: int,
        quantity: int,
        average_cost: float | None = None,
    ) -> None:
        if quantity <= 0:
            raise ValueError("Ponownie otwarta pozycja musi mieć dodatnią ilość.")
        try:
            with self.connection() as conn:
                row = conn.execute(
                    "SELECT average_cost FROM positions WHERE id = ?", (position_id,)
                ).fetchone()
                if row is None:
                    raise ValueError(f"Nie znaleziono pozycji o id {position_id}.")
                new_average_cost = (
                    float(row["average_cost"])
                    if average_cost is None
                    else average_cost
                )
                if new_average_cost <= 0:
                    raise ValueError("Średni koszt musi być większy od zera.")
                conn.execute(
                    """
                    UPDATE positions
                    SET status = ?, quantity = ?, average_cost = ?,
                        sell_date = NULL, sell_price = NULL, realized_gain = NULL
                    WHERE id = ?
                    """,
                    (STATUS_OPEN, quantity, new_average_cost, position_id),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się ponownie otworzyć pozycji: {exc}") from exc

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
            pe_ratio, dividend_yield, debt_to_equity, roe, payout_ratio, revenue_growth_3y, notes,
            fundamental_evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                evidence = self.fundamentals.freeze_review(review, conn)
                cursor = conn.execute(sql, (*review.to_db_tuple()[:-1], evidence))
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się zapisać rewizji: {exc}") from exc

    def insert_review_and_update_position(
        self,
        review: Review,
        current_price: float,
        next_review_date: str,
    ) -> int:
        """Persist a review and its position update in one transaction."""
        if review.position_id <= 0:
            raise ValueError("Rewizja wymaga poprawnego identyfikatora pozycji.")
        if current_price <= 0:
            raise ValueError("Aktualna cena musi być większa od zera.")

        sql = """
        INSERT INTO reviews (
            position_id, review_date, price_then, return_pct, category, instruction,
            pe_ratio, dividend_yield, debt_to_equity, roe, payout_ratio,
            revenue_growth_3y, notes, fundamental_evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self.connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                evidence = self.fundamentals.freeze_review(review, conn)
                cursor = conn.execute(sql, (*review.to_db_tuple()[:-1], evidence))
                updated = conn.execute(
                    """
                    UPDATE positions
                    SET current_price = ?, review_date = ?
                    WHERE id = ? AND status = ?
                    """,
                    (
                        current_price,
                        next_review_date,
                        review.position_id,
                        STATUS_OPEN,
                    ),
                )
                if updated.rowcount != 1:
                    raise ValueError(
                        "Nie znaleziono otwartej pozycji dla zapisywanej rewizji."
                    )
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

    def get_previous_review_for_position(
        self, position_id: int, before_review_id: int | None = None
    ) -> Review | None:
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
            raise RuntimeError(
                f"Nie udało się dodać kategorii assetów {category.name}: {exc}"
            ) from exc

    def get_all_asset_categories(self) -> list[AssetCategory]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM asset_categories ORDER BY sort_order, name COLLATE NOCASE"
            ).fetchall()
        return [AssetCategory.from_row(row) for row in rows]

    def get_asset_category_by_name(self, name: str) -> AssetCategory | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM asset_categories WHERE name = ?", (name,)
            ).fetchone()
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
            raise RuntimeError(
                f"Nie udało się zaktualizować kategorii assetów: {exc}"
            ) from exc

    def update_asset_category_actual(self, name: str, actual_pct: float) -> None:
        try:
            with self.connection() as conn:
                conn.execute(
                    "UPDATE asset_categories SET actual_pct = ? WHERE name = ?",
                    (actual_pct, name),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Nie udało się zaktualizować aktualnej alokacji: {exc}"
            ) from exc

    def delete_asset_category(self, category_id: int) -> None:
        try:
            with self.connection() as conn:
                conn.execute(
                    "DELETE FROM asset_categories WHERE id = ?", (category_id,)
                )
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Nie udało się usunąć kategorii assetów: {exc}"
            ) from exc

    def upsert_market_data(
        self, key: str, value: float, unit: str | None = None
    ) -> None:
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
            raise RuntimeError(
                f"Nie udało się zapisać danych rynkowych {key}: {exc}"
            ) from exc

    def get_market_data(self, key: str) -> MarketData | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM market_data WHERE key = ?", (key,)
            ).fetchone()
        return MarketData.from_row(row) if row else None

    def get_all_market_data(self) -> list[MarketData]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM market_data ORDER BY key COLLATE NOCASE"
            ).fetchall()
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
        total = 0.0

        for position in positions:
            if not include_closed and position.status == STATUS_CLOSED:
                continue

            market_value = PositionValuation.snapshot(position).market_value
            if market_value is not None:
                total += market_value

        return round(total, 2)

    def due_positions(self, on_date: date | None = None) -> list[Position]:
        on_date = on_date or date.today()
        rows: Sequence[sqlite3.Row]
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE status = ? AND review_date <= ? ORDER BY review_date, ticker COLLATE NOCASE",
                (STATUS_OPEN, on_date.isoformat()),
            ).fetchall()
            return [Position.from_row(row) for row in rows]

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

    today = date.today()
    buy_date = today - timedelta(days=220)
    next_review = buy_date + timedelta(days=REVIEW_INTERVAL_DAYS)

    positions = [
        Position(
            ticker="HEN",
            isin="NL0000009165",
            name="Heineken N.V.",
            currency="EUR",
            sector="Akcje / Consumer Defensive",
            thesis="Demo: mocna marka globalna, stabilne przepływy i potencjał poprawy marży.",
            initial_buy_price=82.00,
            initial_buy_date=buy_date.isoformat(),
            quantity=10,
            average_cost=82.00,
            current_price=96.50,
            review_date=next_review.isoformat(),
        ),
        Position(
            ticker="DTG",
            isin="DE000DTR0CK8",
            name="Daimler Truck Holding AG",
            currency="EUR",
            sector="Akcje / Industrials",
            thesis="Demo: ekspozycja na cykl ciężarówek, dyscyplina kosztowa i potencjał dywidendowy.",
            initial_buy_price=34.20,
            initial_buy_date=(buy_date - timedelta(days=30)).isoformat(),
            quantity=20,
            average_cost=34.20,
            current_price=31.80,
            review_date=(next_review - timedelta(days=30)).isoformat(),
        ),
        Position(
            ticker="FME",
            isin="DE0005785802",
            name="Fresenius Medical Care AG",
            currency="EUR",
            sector="Akcje / Healthcare",
            thesis="Demo: restrukturyzacja, defensywny popyt i możliwy powrót ROE do średniej historycznej.",
            initial_buy_price=42.50,
            initial_buy_date=(buy_date - timedelta(days=60)).isoformat(),
            quantity=12,
            average_cost=42.50,
            current_price=47.20,
            review_date=(next_review - timedelta(days=60)).isoformat(),
        ),
    ]

    inserted: dict[str, int] = {}
    for position in positions:
        inserted[position.ticker] = db.insert_position(position)

    from src.rule_engine import categorize_with_thresholds

    hen_position = db.get_position_by_id(inserted["HEN"])
    if hen_position is not None:
        return_pct = PositionValuation.snapshot(hen_position).unrealized_return
        if return_pct is None:
            return
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


def get_all_positions(
    include_closed: bool = False, db_path: Path = DB_PATH
) -> list[Position]:
    return Database(db_path).get_all_positions(include_closed=include_closed)


def update_position(position: Position, db_path: Path = DB_PATH) -> None:
    Database(db_path).update_position(position)


def delete_position(position_id: int, db_path: Path = DB_PATH) -> None:
    Database(db_path).delete_position(position_id)


def insert_review(review: Review, db_path: Path = DB_PATH) -> int:
    return Database(db_path).insert_review(review)


def get_reviews_for_position(position_id: int, db_path: Path = DB_PATH) -> list[Review]:
    return Database(db_path).get_reviews_for_position(position_id)


def get_last_review_for_position(
    position_id: int, db_path: Path = DB_PATH
) -> Review | None:
    return Database(db_path).get_last_review_for_position(position_id)


def insert_asset_category(category: AssetCategory, db_path: Path = DB_PATH) -> int:
    return Database(db_path).insert_asset_category(category)


def get_all_asset_categories(db_path: Path = DB_PATH) -> list[AssetCategory]:
    return Database(db_path).get_all_asset_categories()


def update_asset_category(category: AssetCategory, db_path: Path = DB_PATH) -> None:
    Database(db_path).update_asset_category(category)


def upsert_market_data(
    key: str, value: float, unit: str | None = None, db_path: Path = DB_PATH
) -> None:
    Database(db_path).upsert_market_data(key, value, unit)


def get_market_data(key: str, db_path: Path = DB_PATH) -> MarketData | None:
    return Database(db_path).get_market_data(key)
