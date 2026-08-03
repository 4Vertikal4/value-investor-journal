from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QMenu, QTableView

from src.config import CATEGORY_STYLES, STATUS_CLOSED
from src.models import Position
from src.rule_engine import calculate_return, categorize_with_thresholds, format_return


class PositionTableModel(QAbstractTableModel):
    HEADERS = (
        "Ticker",
        "Nazwa",
        "Cena zakupu",
        "Aktualna",
        "Zwrot %",
        "Kategoria",
        "Instrukcja",
        "Data rewizji",
        "Status",
    )

    def __init__(self, positions: list[Position] | None = None) -> None:
        super().__init__()
        self.positions = positions or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.positions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        position = self.positions[index.row()]
        column = index.column()
        category, instruction, return_pct = self._status_for_position(position)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_value(
                position, column, category, instruction, return_pct
            )
        if role == Qt.ItemDataRole.UserRole:
            return position.id
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column in {2, 3, 4}:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.BackgroundRole:
            style_key = STATUS_CLOSED if position.status == STATUS_CLOSED else category
            return QColor(
                CATEGORY_STYLES.get(style_key, CATEGORY_STYLES["NEUTRALNY"])["bg"]
            )
        if role == Qt.ItemDataRole.ForegroundRole:
            style_key = STATUS_CLOSED if position.status == STATUS_CLOSED else category
            return QColor(
                CATEGORY_STYLES.get(style_key, CATEGORY_STYLES["NEUTRALNY"])["fg"]
            )
        if role == Qt.ItemDataRole.FontRole:
            font = QFont()
            if column in {0, 5, 6}:
                font.setBold(True)
            if position.status == STATUS_CLOSED:
                font.setStrikeOut(True)
            return font
        return None

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        reverse = order == Qt.SortOrder.DescendingOrder
        self.layoutAboutToBeChanged.emit()
        self.positions.sort(key=self.sort_key, reverse=reverse)
        self.layoutChanged.emit()

    def sort_key(self, position: Position) -> Any:
        category, instruction, return_pct = self._status_for_position(position)
        values = (
            position.ticker,
            position.name,
            position.buy_price,
            position.display_price(),
            return_pct,
            category,
            instruction,
            position.review_date,
            position.status,
        )
        return values[column]

    def set_positions(self, positions: list[Position]) -> None:
        self.beginResetModel()
        self.positions = list(positions)
        self.endResetModel()

    def position_at(self, row: int) -> Position | None:
        if 0 <= row < len(self.positions):
            return self.positions[row]
        return None

    @staticmethod
    def _status_for_position(position: Position) -> tuple[str, str, float]:
        current = position.display_price()
        return_pct = calculate_return(position.buy_price, current)
        category, instruction = categorize_with_thresholds(
            return_pct,
            position.sell_threshold_gain,
            position.sell_threshold_profit,
            position.sell_threshold_loss,
        )
        return category, instruction, return_pct

    @staticmethod
    def _display_value(
        position: Position,
        column: int,
        category: str,
        instruction: str,
        return_pct: float,
    ) -> str:
        values = (
            position.ticker,
            position.name,
            f"{position.buy_price:.4f} {position.currency}",
            f"{position.display_price():.4f} {position.currency}",
            format_return(return_pct),
            category,
            instruction,
            position.review_date,
            position.status,
        )
        return values[column]


class DashboardTable(QTableView):
    positionDoubleClicked = Signal(object)
    contextMenuRequestedForPosition = Signal(object, QPoint)
    selectionChangedForPosition = Signal(object)

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.model_obj = PositionTableModel()
        self.setModel(self.model_obj)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.doubleClicked.connect(self._emit_double_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._emit_context_menu)
        self.selectionModel().selectionChanged.connect(self._emit_selection_changed)

    def set_positions(self, positions: list[Position]) -> None:
        self.model_obj.set_positions(positions)
        self.resizeColumnsToContents()
        if positions:
            self.selectRow(0)

    def selected_position(self) -> Position | None:
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.model_obj.position_at(indexes[0].row())

    def position_from_index(self, index: QModelIndex) -> Position | None:
        if not index.isValid():
            return None
        return self.model_obj.position_at(index.row())

    def _emit_double_clicked(self, index: QModelIndex) -> None:
        position = self.position_from_index(index)
        if position is not None:
            self.positionDoubleClicked.emit(position)

    def _emit_context_menu(self, point: QPoint) -> None:
        index = self.indexAt(point)
        position = self.position_from_index(index)
        if position is not None:
            self.contextMenuRequestedForPosition.emit(
                position, self.viewport().mapToGlobal(point)
            )

    def _emit_selection_changed(self) -> None:
        self.selectionChangedForPosition.emit(self.selected_position())

    def create_default_context_menu(
        self, position: Position, parent: object | None = None
    ) -> QMenu:
        menu = QMenu(parent)
        menu.addAction(f"Dodaj rewizję dla {position.ticker}")
        menu.addAction("Zamknij pozycję")
        menu.addSeparator()
        menu.addAction("Usuń")
        return menu
