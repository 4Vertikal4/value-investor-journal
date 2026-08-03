from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.config import DEFAULT_CURRENCY, REVIEW_INTERVAL_DAYS
from src.database import Database
from src.models import Position


@dataclass(slots=True)
class ImportResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


COLUMN_ALIASES = {
    "ticker": (
        "ticker",
        "symbol",
        "instrument ticker",
        "instrument symbol",
        "isin ticker",
        "stock ticker",
    ),
    "name": (
        "name",
        "instrument",
        "instrument name",
        "security name",
        "description",
        "company",
    ),
    "side": (
        "side",
        "type",
        "transaction type",
        "activity type",
        "action",
        "operation",
    ),
    "date": (
        "date",
        "trade date",
        "transaction date",
        "executed at",
        "time",
        "created at",
    ),
    "price": (
        "price",
        "unit price",
        "share price",
        "execution price",
        "average price",
        "fill price",
    ),
    "quantity": ("quantity", "qty", "shares", "units", "filled quantity"),
    "amount": (
        "amount",
        "total",
        "value",
        "gross amount",
        "net amount",
        "consideration",
    ),
    "currency": ("currency", "ccy", "price currency", "settlement currency"),
}

BUY_WORDS = ("buy", "bought", "purchase", "market buy", "limit buy", "kupno", "zakup")
SELL_WORDS = ("sell", "sold", "market sell", "limit sell", "sprzedaż", "sprzedaz")


def _normalise_column(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _find_column(columns: Iterable[str], aliases: Iterable[str]) -> str | None:
    normalised = {_normalise_column(column): column for column in columns}
    for alias in aliases:
        key = _normalise_column(alias)
        if key in normalised:
            return normalised[key]
    for normalised_name, original in normalised.items():
        if any(_normalise_column(alias) in normalised_name for alias in aliases):
            return original
    return None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def _cell(row: pd.Series, column: str | None) -> Any:
    if column is None:
        return None
    value = row.get(column)
    return None if _is_empty(value) else value


def _parse_float(value: Any) -> float | None:
    if _is_empty(value):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    text = text.replace("%", "")
    text = re.sub(r"[^0-9,\.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(value: Any) -> str:
    if _is_empty(value):
        return date.today().isoformat()
    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return date.today().isoformat()
    return parsed.date().isoformat()


def _action_allows_import(value: Any) -> bool:
    if _is_empty(value):
        return True
    text = str(value).lower()
    if any(word in text for word in SELL_WORDS):
        return False
    return any(word in text for word in BUY_WORDS) or True


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=None, engine="python", encoding="latin-1")


def import_lightyear_csv(path: Path, database: Database) -> ImportResult:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku: {path}")

    df = _read_csv(path)
    result = ImportResult()
    columns = list(df.columns)
    mapped = {
        key: _find_column(columns, aliases) for key, aliases in COLUMN_ALIASES.items()
    }

    if mapped["ticker"] is None and mapped["name"] is None:
        raise ValueError(
            "CSV nie wygląda jak eksport Lightyear: brak kolumny ticker/symbol albo nazwy instrumentu."
        )

    for row_index, row in df.iterrows():
        try:
            if not _action_allows_import(_cell(row, mapped["side"])):
                result.skipped += 1
                continue

            ticker_value = _cell(row, mapped["ticker"])
            name_value = _cell(row, mapped["name"])
            ticker = str(ticker_value or name_value or "").strip().upper()
            ticker = re.sub(r"\s+", "", ticker)[:10]
            name = str(name_value or ticker).strip()
            if not ticker:
                result.skipped += 1
                continue

            price = _parse_float(_cell(row, mapped["price"]))
            quantity = _parse_float(_cell(row, mapped["quantity"]))
            amount = _parse_float(_cell(row, mapped["amount"]))
            if price is None and amount is not None and quantity not in {None, 0.0}:
                price = abs(amount / quantity)
            if price is None or price <= 0:
                result.skipped += 1
                continue

            buy_date = _parse_date(_cell(row, mapped["date"]))
            currency = (
                str(_cell(row, mapped["currency"]) or DEFAULT_CURRENCY)
                .strip()
                .upper()[:3]
            )
            existing = database.get_position_by_ticker(ticker)
            if existing is None:
                review_date = (
                    date.fromisoformat(buy_date) + timedelta(days=REVIEW_INTERVAL_DAYS)
                ).isoformat()
                position = Position(
                    ticker=ticker,
                    name=name,
                    sector="Akcje / Lightyear",
                    thesis=f"Import z pliku Lightyear: {path.name}",
                    buy_price=price,
                    current_price=price,
                    buy_date=buy_date,
                    review_date=review_date,
                    currency=currency or DEFAULT_CURRENCY,
                )
                database.insert_position(position)
                result.inserted += 1
            else:
                existing.current_price = price
                if not existing.name or existing.name == existing.ticker:
                    existing.name = name
                database.update_position(existing)
                result.updated += 1
        except Exception as exc:
            result.errors.append(f"Wiersz {row_index + 2}: {exc}")
    return result
