

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.config import (
    DEFAULT_CURRENCY,
    REVIEW_INTERVAL_DAYS,
    STATUS_CLOSED,
    STATUS_OPEN,
)
from src.database import Database
from src.models import Position


@dataclass(slots=True)
class ImportResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


COLUMN_ALIASES = {
    "isin": (
        "isin",
        "instrument isin",
        "security isin",
    ),
    "ticker": (
        "ticker",
        "symbol",
        "instrument ticker",
        "instrument symbol",
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
SKIP_WORDS = (
    "dividend",
    "dywidenda",
    "conversion",
    "konwersja",
    "deposit",
    "wpłata",
    "wplata",
    "withdrawal",
    "wypłata",
    "wyplata",
    "interest",
    "odsetki",
)


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
        raise ValueError("Brak daty transakcji.")
    text = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}(?:$|[ T])", text):
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except ValueError as exc:
            raise ValueError(f"Nieprawidłowa data transakcji: {value!r}.") from exc
    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Nieprawidłowa data transakcji: {value!r}.")
    return parsed.date().isoformat()


def _date_sort_key(value: Any) -> str:
    try:
        return _parse_date(value)
    except ValueError:
        return "9999-12-31"


def _classify_action(value: Any) -> str:
    if _is_empty(value):
        return "BUY"
    text = str(value).lower()
    if any(word in text for word in SKIP_WORDS):
        return "SKIP"
    if any(word in text for word in SELL_WORDS):
        return "SELL"
    if any(word in text for word in BUY_WORDS):
        return "BUY"
    return "SKIP"


def _normalise_isin(value: Any) -> str:
    if _is_empty(value):
        return ""
    return re.sub(r"\s+", "", str(value)).upper()


def _parse_quantity(value: Any) -> int | None:
    parsed = _parse_float(value)
    if parsed is None or parsed <= 0:
        return None
    rounded = round(parsed)
    if not math.isclose(parsed, rounded, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(
            "Model Position obsługuje wyłącznie całkowitą liczbę akcji."
        )
    return int(rounded)


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

    if mapped["isin"] is None:
        raise ValueError(
            "CSV nie wygląda jak eksport Lightyear: brak kolumny ISIN."
        )

    rows = list(df.iterrows())
    if mapped["date"] is not None:
        rows.sort(
            key=lambda item: _date_sort_key(_cell(item[1], mapped["date"]))
        )

    for row_index, row in rows:
        try:
            action = _classify_action(_cell(row, mapped["side"]))
            if action == "SKIP":
                result.skipped += 1
                continue

            isin = _normalise_isin(_cell(row, mapped["isin"]))
            if not isin:
                result.errors.append(f"Wiersz {row_index + 2}: brak ISIN.")
                result.skipped += 1
                continue

            ticker_value = _cell(row, mapped["ticker"])
            name_value = _cell(row, mapped["name"])
            ticker = re.sub(
                r"\s+", "", str(ticker_value or isin).strip().upper()
            )
            name = str(name_value).strip() if name_value is not None else None

            price = _parse_float(_cell(row, mapped["price"]))
            quantity = _parse_quantity(_cell(row, mapped["quantity"]))
            amount = _parse_float(_cell(row, mapped["amount"]))
            if price is None and amount is not None and quantity not in {None, 0.0}:
                price = abs(amount / quantity)
            if price is None or price <= 0 or quantity is None:
                result.skipped += 1
                continue

            transaction_date = _parse_date(_cell(row, mapped["date"]))
            currency = (
                str(_cell(row, mapped["currency"]) or DEFAULT_CURRENCY)
                .strip()
                .upper()[:3]
            )
            existing = database.get_position_by_isin(isin)
            if existing is None:
                if action == "SELL":
                    raise ValueError(
                        f"Sprzedaż {isin} nie ma odpowiadającej otwartej pozycji."
                    )
                review_date = (
                    date.fromisoformat(transaction_date)
                    + timedelta(days=REVIEW_INTERVAL_DAYS)
                ).isoformat()
                position = Position(
                    ticker=ticker,
                    isin=isin,
                    name=name,
                    currency=currency or DEFAULT_CURRENCY,
                    sector="Akcje / Lightyear",
                    thesis=f"Import z pliku Lightyear: {path.name}",
                    initial_buy_price=price,
                    initial_buy_date=transaction_date,
                    quantity=quantity,
                    average_cost=price,
                    current_price=None,
                    review_date=review_date,
                )
                database.insert_position(position)
                result.inserted += 1
                continue

            if existing.currency != currency:
                raise ValueError(
                    f"Waluta {currency} nie zgadza się z walutą pozycji "
                    f"{existing.currency} dla {isin}."
                )

            previous_ticker = existing.ticker
            if ticker:
                existing.ticker = ticker
            if name and (not existing.name or existing.name == previous_ticker):
                existing.name = name

            if action == "BUY":
                previous_quantity = existing.quantity
                new_quantity = previous_quantity + quantity
                if previous_quantity == 0:
                    existing.average_cost = price
                else:
                    existing.average_cost = (
                        previous_quantity * existing.average_cost + quantity * price
                    ) / new_quantity
                existing.quantity = new_quantity
                if existing.status == STATUS_CLOSED:
                    existing.status = STATUS_OPEN
                    existing.sell_date = None
                    existing.sell_price = None
                    existing.realized_gain = None
                database.update_position(existing)
            else:
                if existing.status == STATUS_CLOSED or existing.quantity == 0:
                    raise ValueError(f"Pozycja {isin} jest już zamknięta.")
                if quantity > existing.quantity:
                    raise ValueError(
                        f"Sprzedaż {quantity} akcji przekracza posiadane "
                        f"{existing.quantity} dla {isin}."
                    )
                if quantity == existing.quantity:
                    if existing.id is None:
                        raise ValueError("Pozycja nie ma identyfikatora bazy danych.")
                    database.close_position(
                        existing.id,
                        sell_price=price,
                        sell_date=transaction_date,
                    )
                else:
                    existing.quantity -= quantity
                    database.update_position(existing)
            result.updated += 1
        except Exception as exc:
            result.errors.append(f"Wiersz {row_index + 2}: {exc}")
    return result
