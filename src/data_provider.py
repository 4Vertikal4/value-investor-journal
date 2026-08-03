from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.database import Database


class DataProvider(ABC):
    @abstractmethod
    def get_current_data(self) -> dict[str, Any]:
        raise NotImplementedError("Provider musi zwrócić aktualne dane.")


class ManualDataProvider(DataProvider):
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_current_data(self) -> dict[str, Any]:
        return {
            item.key: {
                "value": item.value,
                "unit": item.unit,
                "updated_at": item.updated_at,
            }
            for item in self.database.get_all_market_data()
        }

    def set_value(
        self,
        key: str,
        value: float,
        unit: str | None = None,
    ) -> None:
        self.database.upsert_market_data(key, value, unit)


class YahooDataProvider(DataProvider):
    def get_current_data(self) -> dict[str, Any]:
        raise RuntimeError(
            "Provider Yahoo Finance nie jest aktywny w wersji offline-first."
        )
