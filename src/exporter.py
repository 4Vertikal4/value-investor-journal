from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from src.database import Database


def _positions_dataframe(database: Database) -> pd.DataFrame:
    positions = [
        position.to_dict()
        for position in database.get_all_positions(include_closed=True)
    ]
    return pd.DataFrame(positions)


def _reviews_dataframe(database: Database) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for position in database.get_all_positions(include_closed=True):
        for review in database.get_reviews_for_position(position.id or 0):
            item = review.to_dict()
            item["ticker"] = position.ticker
            item["name"] = position.name
            rows.append(item)
    return pd.DataFrame(rows)


def _asset_categories_dataframe(database: Database) -> pd.DataFrame:
    return pd.DataFrame(
        [category.to_dict() for category in database.get_all_asset_categories()]
    )


def _market_data_dataframe(database: Database) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "key": item.key,
                "value": item.value,
                "unit": item.unit,
                "updated_at": item.updated_at,
            }
            for item in database.get_all_market_data()
        ]
    )


def export_positions_csv(path: Path, database: Database) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _positions_dataframe(database).to_csv(path, index=False)
    return path


def export_reviews_csv(path: Path, database: Database) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reviews_dataframe(database).to_csv(path, index=False)
    return path


def export_xlsx(path: Path, database: Database) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheets = {
            "Pozycje": _positions_dataframe(database),
            "Rewizje": _reviews_dataframe(database),
            "Alokacja": _asset_categories_dataframe(database),
            "MarketData": _market_data_dataframe(database),
        }
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
            worksheet = writer.sheets[sheet_name]
            for column_cells in worksheet.columns:
                max_length = max(
                    (
                        len(str(cell.value))
                        for cell in column_cells
                        if cell.value is not None
                    ),
                    default=10,
                )
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(
                    max(max_length + 2, 12), 42
                )
    return path


def backup_database(path: Path, database: Database) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(database.db_path, path)
    return path
