from __future__ import annotations

import sqlite3

from datetime import date
from pathlib import Path

from src.config import (
    DB_PATH,
    SQLITE_TIMEOUT,
    SQLITE_JOURNAL_MODE,
    ENABLE_DEMO_DATA,
)
from src.models import (
    Position,
    PositionStatus,
    Review,
    AssetCategory,
    Event,
    EventStatus,
    EventTriggerType,
)

# ============================================================
# CONNECTION
# ============================================================


def get_connection() -> sqlite3.Connection:
    """
    Tworzy połączenie SQLite z poprawną konfiguracją.
    """
    connection = sqlite3.connect(
        DB_PATH,
        timeout=SQLITE_TIMEOUT,
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute(f"PRAGMA journal_mode = {SQLITE_JOURNAL_MODE};")

    return connection


# ============================================================
# DATABASE INIT
# ============================================================


def init_db() -> None:
    """
    Tworzy wszystkie wymagane tabele SQLite.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        # ====================================================
        # POSITIONS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                ticker TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                sector TEXT,
                thesis TEXT,

                quantity REAL NOT NULL DEFAULT 1.0,

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
            """)

        # ====================================================
        # REVIEWS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                position_id INTEGER NOT NULL,

                review_date TEXT DEFAULT CURRENT_DATE,

                price_then REAL NOT NULL,
                return_pct REAL NOT NULL,

                category TEXT NOT NULL,
                instruction TEXT NOT NULL,

                notes TEXT,

                FOREIGN KEY (position_id)
                    REFERENCES positions(id)
                    ON DELETE CASCADE
            );
            """)

        # ====================================================
        # ASSET CATEGORIES
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL UNIQUE,

                target_pct REAL NOT NULL,
                actual_pct REAL DEFAULT 0.0,

                color TEXT DEFAULT '#3DAEE9',

                icon_path TEXT,

                sort_order INTEGER DEFAULT 0
            );
            """)

        # ====================================================
        # EVENTS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,
                description TEXT,

                trigger_type TEXT NOT NULL,
                trigger_condition TEXT NOT NULL,

                action_message TEXT NOT NULL,

                image_path TEXT,

                status TEXT DEFAULT 'ACTIVE',

                created_date TEXT,
                triggered_date TEXT,
                dismissed_date TEXT,
                expires_date TEXT
            );
            """)

        # ====================================================
        # EVENT LOGS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_id INTEGER NOT NULL,

                triggered_at TEXT DEFAULT CURRENT_TIMESTAMP,

                user_action TEXT,
                notes TEXT,

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
                    ON DELETE CASCADE
            );
            """)

        # ====================================================
        # MARKET DATA
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                key TEXT PRIMARY KEY,

                value REAL NOT NULL,

                unit TEXT,
                updated_at TEXT
            );
            """)

        # ====================================================
        # INDEXES
        # ====================================================

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_position_id
            ON reviews(position_id);
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_status
            ON events(status);
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_status
            ON positions(status);
            """)

        connection.commit()

    if ENABLE_DEMO_DATA:
        seed_demo_data()


# ============================================================
# POSITION CRUD
# ============================================================


def insert_position(position: Position) -> int:
    """
    Dodaje pozycję do bazy.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO positions (
                ticker,
                name,
                sector,
                thesis,
                quantity,
                buy_price,
                buy_date,
                review_date,
                currency,
                sell_threshold_gain,
                sell_threshold_profit,
                sell_threshold_loss,
                status,
                current_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position.ticker,
                position.name,
                position.sector,
                position.thesis,
                position.quantity,
                position.buy_price,
                position.buy_date,
                position.review_date,
                position.currency,
                position.sell_threshold_gain,
                position.sell_threshold_profit,
                position.sell_threshold_loss,
                position.status.value,
                position.current_price,
            ),
        )

        connection.commit()

        return int(cursor.lastrowid)


def get_all_positions() -> list[Position]:
    """
    Zwraca wszystkie pozycje.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM positions
            ORDER BY review_date ASC;
            """)

        rows = cursor.fetchall()

        return [Position.from_row(row) for row in rows]


def get_position_by_id(position_id: int) -> Position | None:
    """
    Pobiera pozycję po ID.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM positions
            WHERE id = ?
            """,
            (position_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return Position.from_row(row)


def update_position(position: Position) -> None:
    """
    Aktualizuje pozycję.
    """

    if position.id is None:
        raise ValueError("Position ID cannot be None during update.")

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE positions
            SET
                name = ?,
                sector = ?,
                thesis = ?,
                quantity = ?,
                buy_price = ?,
                buy_date = ?,
                review_date = ?,
                currency = ?,
                sell_threshold_gain = ?,
                sell_threshold_profit = ?,
                sell_threshold_loss = ?,
                status = ?,
                current_price = ?
            WHERE id = ?
            """,
            (
                position.name,
                position.sector,
                position.thesis,
                position.quantity,
                position.buy_price,
                position.buy_date,
                position.review_date,
                position.currency,
                position.sell_threshold_gain,
                position.sell_threshold_profit,
                position.sell_threshold_loss,
                position.status.value,
                position.current_price,
                position.id,
            ),
        )

        connection.commit()


def delete_position(position_id: int) -> None:
    """
    Usuwa pozycję.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM positions
            WHERE id = ?
            """,
            (position_id,),
        )

        connection.commit()


# ============================================================
# REVIEW CRUD
# ============================================================


def insert_review(review: Review) -> int:
    """
    Dodaje rewizję.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO reviews (
                position_id,
                review_date,
                price_then,
                return_pct,
                category,
                instruction,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review.position_id,
                review.review_date,
                review.price_then,
                review.return_pct,
                review.category.value,
                review.instruction.value,
                review.notes,
            ),
        )

        connection.commit()

        return int(cursor.lastrowid)


def get_reviews_for_position(position_id: int) -> list[Review]:
    """
    Pobiera rewizje dla pozycji.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM reviews
            WHERE position_id = ?
            ORDER BY review_date DESC
            """,
            (position_id,),
        )

        rows = cursor.fetchall()

        return [Review.from_row(row) for row in rows]


# ============================================================
# DEMO DATA
# ============================================================


def seed_demo_data() -> None:
    """
    Seeduje przykładowe dane jeśli baza jest pusta.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM positions;")

        count = cursor.fetchone()[0]

        if count > 0:
            return

    demo_positions = [
        Position(
            id=None,
            ticker="HEN3",
            name="Henkel AG",
            sector="Consumer Goods",
            thesis="Stabilny value stock z silną marką.",
            quantity=10.0,
            buy_price=72.50,
            current_price=81.20,
            buy_date="2025-02-10",
            review_date="2026-02-10",
            currency="EUR",
            sell_threshold_gain=0.20,
            sell_threshold_profit=0.10,
            sell_threshold_loss=-0.10,
            status=PositionStatus.OPEN,
        ),
        Position(
            id=None,
            ticker="FME",
            name="Fresenius Medical Care",
            sector="Healthcare",
            thesis="Defensywny healthcare z potencjałem odbicia.",
            quantity=15.0,
            buy_price=34.00,
            current_price=37.50,
            buy_date="2025-01-15",
            review_date="2026-01-15",
            currency="EUR",
            sell_threshold_gain=0.20,
            sell_threshold_profit=0.10,
            sell_threshold_loss=-0.10,
            status=PositionStatus.OPEN,
        ),
    ]

    for position in demo_positions:
        insert_position(position)

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO asset_categories (
                name,
                target_pct,
                actual_pct,
                color,
                sort_order
            )
            VALUES
                ('Akcje', 0.60, 0.0, '#3DAEE9', 1),
                ('Obligacje', 0.30, 0.0, '#90EE90', 2),
                ('Złoto', 0.10, 0.0, '#FFD700', 3)
            """)

        cursor.execute(
            """
            INSERT OR IGNORE INTO events (
                name,
                description,
                trigger_type,
                trigger_condition,
                action_message,
                status,
                created_date
            )
            VALUES (
                'FED podnosi stopy o 2%',
                'Przykładowe wydarzenie makroekonomiczne.',
                'MANUAL',
                '{"metric":"manual","op":"==","value":true}',
                'Zmniejsz ekspozycję na akcje do 40%.',
                'ACTIVE',
                ?
            )
            """,
            (date.today().isoformat(),),
        )

        connection.commit()
