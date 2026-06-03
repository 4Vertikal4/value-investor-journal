from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableView,
)

from src.config import CATEGORY_COLORS
from src.models import Position


class DashboardTableModel(QAbstractTableModel):
    """
    Model danych dla głównej tabeli pozycji.
    """

    HEADERS = [
        "Ticker",
        "Nazwa",
        "Ilość",
        "Cena zakupu",
        "Aktualna",
        "Wartość",
        "Zwrot %",
        "Data rewizji",
        "Status",
    ]

    def __init__(
        self,
        positions: list[Position] | None = None,
    ) -> None:
        super().__init__()

        self._positions = positions or []

    def _format_quantity(
        self,
        quantity: float,
    ) -> str:
        """
        Ładne wyświetlanie ilości.

        10.0000 -> 10
        10.5000 -> 10.5
        10.1250 -> 10.125
        """

        if quantity.is_integer():
            return str(int(quantity))

        return f"{quantity:.4f}".rstrip("0").rstrip(".")

    # ========================================================
    # DATA MANAGEMENT
    # ========================================================

    def set_positions(
        self,
        positions: list[Position],
    ) -> None:
        self.beginResetModel()
        self._positions = positions
        self.endResetModel()

    def get_position(
        self,
        row: int,
    ) -> Position | None:
        if row < 0:
            return None

        if row >= len(self._positions):
            return None

        return self._positions[row]

    # ========================================================
    # QT MODEL API
    # ========================================================

    def rowCount(
        self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        return len(self._positions)

    def columnCount(
        self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        return len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]

        return None

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        position = self._positions[index.row()]
        column = index.column()

        # ====================================================
        # DISPLAY
        # ====================================================

        if role == Qt.DisplayRole:

            match column:

                case 0:
                    return position.ticker

                case 1:
                    return position.name

                case 2:
                    return self._format_quantity(position.quantity)

                case 3:
                    return f"{position.buy_price:.2f}"

                case 4:
                    if position.current_price is None:
                        return "-"

                    return f"{position.current_price:.2f}"

                case 5:
                    return f"{position.market_value:.2f}"

                case 6:
                    return f"{position.return_pct:.2f}%"

                case 7:
                    return position.review_date

                case 8:
                    return position.status.value

        # ====================================================
        # ALIGNMENT
        # ====================================================

        if role == Qt.TextAlignmentRole:
            if column in (2, 3, 4, 5, 6):
                return Qt.AlignRight | Qt.AlignVCenter

        # ====================================================
        # TEXT COLOR
        # ====================================================

        if role == Qt.ForegroundRole:
            return self._get_text_color(position)

        return None

    # ========================================================
    # COLORS
    # ========================================================

    def _get_text_color(
        self,
        position: Position,
    ) -> QColor | None:
        try:
            if position.return_pct >= 20:
                return QColor(CATEGORY_COLORS["RZUCAM SZTABKAMI"]["text"])

            if position.return_pct >= 10:
                return QColor(CATEGORY_COLORS["ZAROBEK"]["text"])

            if position.return_pct >= -10:
                return QColor(CATEGORY_COLORS["NEUTRALNY"]["text"])

            return QColor(CATEGORY_COLORS["WYNIK NEGATYWNY"]["text"])

        except KeyError:
            return None


class DashboardTableView(QTableView):
    """
    Główna tabela pozycji inwestycyjnych.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setAlternatingRowColors(True)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setSortingEnabled(True)

        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalHeader().setVisible(False)

        header = self.horizontalHeader()

        header.setStretchLastSection(True)

        header.setSectionResizeMode(QHeaderView.ResizeToContents)
