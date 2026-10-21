from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QDate, QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTableView,
    QWidget,
)

from src.config import CATEGORY_NEUTRAL, CATEGORY_STYLES, STATUS_CLOSED
from src.models import Position, PositionSnapshot, PositionValuation
from src.rule_engine import categorize_with_thresholds


COL_TICKER = 0
COL_NAME = 1
COL_CURRENT_PRICE = 2
COL_MARKET_VALUE = 3
COL_RETURN = 4
COL_CATEGORY = 5
COL_REVIEW = 6
COL_THRESHOLD_DISTANCE = 7

COLOR_POSITIVE = "#90EE90"
COLOR_NEGATIVE = "#FF6B6B"
COLOR_TODAY = "#FFA500"


def _format_money(
    value: float, currency: str, decimals: int = 2, grouped: bool = False
) -> str:
    pattern = f",.{decimals}f" if grouped else f".{decimals}f"
    formatted = format(value, pattern)
    if grouped:
        formatted = formatted.replace(",", " ")
    return f"{formatted} {currency}"


def _format_signed_pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:+.{decimals}f}%"


def _parse_iso_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _to_qdate(value: date | None) -> QDate | None:
    if value is None:
        return None
    return QDate(value.year, value.month, value.day)


@dataclass(frozen=True, slots=True, init=False)
class PositionRow:
    """Cached presentation data shared by display, colors, sorting and tooltips."""

    position: Position
    snapshot: PositionSnapshot
    return_pct: float | None
    category: str | None
    instruction: str | None
    review_date: date | None
    review_days_delta: int | None
    threshold_display: str
    threshold_sort_value: float | None
    threshold_color: str | None

    def __init__(
        self, position: Position, today: date | None = None
    ) -> None:
        """Build one immutable row and calculate its valuation only once."""
        today = today or date.today()
        snapshot = PositionValuation.snapshot(position)
        return_pct = (
            position.realized_gain
            if position.status == STATUS_CLOSED
            else snapshot.unrealized_return
        )

        if return_pct is None:
            category = None
            instruction = None
        else:
            category, instruction = categorize_with_thresholds(
                return_pct,
                position.sell_threshold_gain,
                position.sell_threshold_profit,
                position.sell_threshold_loss,
            )

        review_date = _parse_iso_date(position.review_date)
        review_days_delta = (
            (review_date - today).days if review_date is not None else None
        )
        threshold_display, threshold_sort_value, threshold_color = (
            self._threshold_presentation(position, snapshot)
        )

        object.__setattr__(self, "position", position)
        object.__setattr__(self, "snapshot", snapshot)
        object.__setattr__(self, "return_pct", return_pct)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "instruction", instruction)
        object.__setattr__(self, "review_date", review_date)
        object.__setattr__(self, "review_days_delta", review_days_delta)
        object.__setattr__(self, "threshold_display", threshold_display)
        object.__setattr__(self, "threshold_sort_value", threshold_sort_value)
        object.__setattr__(self, "threshold_color", threshold_color)

    @classmethod
    def from_position(
        cls, position: Position, today: date | None = None
    ) -> "PositionRow":
        return cls(position, today)

    @staticmethod
    def _threshold_presentation(
        position: Position, snapshot: PositionSnapshot
    ) -> tuple[str, float | None, str | None]:
        return_pct = snapshot.unrealized_return
        if position.status == STATUS_CLOSED or return_pct is None:
            return "—", None, None

        if return_pct >= position.sell_threshold_gain:
            return "ZAROBEK", 0.0, COLOR_POSITIVE
        if return_pct <= position.sell_threshold_loss:
            return "REALIZUJ", 0.0, COLOR_NEGATIVE

        distance_to_gain = snapshot.distance_to_gain_pct
        distance_to_loss = snapshot.distance_to_loss_pct
        if return_pct > 0 and distance_to_gain is not None:
            return (
                _format_signed_pct(distance_to_gain),
                distance_to_gain,
                COLOR_POSITIVE,
            )
        if return_pct < 0 and distance_to_loss is not None:
            signed_distance = -abs(distance_to_loss)
            return (
                _format_signed_pct(signed_distance),
                signed_distance,
                COLOR_NEGATIVE,
            )

        # At exactly 0%, show the mathematically nearest threshold.
        candidates: list[tuple[float, str]] = []
        if distance_to_gain is not None:
            candidates.append((distance_to_gain, COLOR_POSITIVE))
        if distance_to_loss is not None:
            candidates.append((-abs(distance_to_loss), COLOR_NEGATIVE))
        if not candidates:
            return "—", None, None
        nearest, color = min(candidates, key=lambda item: abs(item[0]))
        return _format_signed_pct(nearest), nearest, color

    def display_value(self, column: int) -> str:
        position = self.position
        values = (
            position.ticker,
            position.name or "—",
            (
                _format_money(position.current_price, position.currency)
                if position.current_price is not None
                else "—"
            ),
            (
                _format_money(
                    self.snapshot.market_value,
                    position.currency,
                    grouped=True,
                )
                if self.snapshot.market_value is not None
                else "—"
            ),
            (
                _format_signed_pct(self.return_pct)
                if self.return_pct is not None
                else "—"
            ),
            (
                self.category
                if self.category is not None
                else "Brak ceny"
                if position.status != STATUS_CLOSED
                and position.current_price is None
                else "—"
            ),
            self.review_display(),
            self.threshold_display,
        )
        return values[column]

    def review_display(self) -> str:
        if self.review_date is None or self.review_days_delta is None:
            return "—"
        if self.review_days_delta < 0:
            days = abs(self.review_days_delta)
            return f"przeterminowana o {days} dni"
        if self.review_days_delta == 0:
            return "dziś"
        return self.review_date.strftime("%d.%m")

    def sort_value(self, column: int) -> str | int | float | None:
        position = self.position
        values: tuple[str | int | float | None, ...] = (
            position.ticker.casefold(),
            position.name.casefold() if position.name else None,
            position.current_price,
            self.snapshot.market_value,
            self.return_pct,
            self.category.casefold() if self.category else None,
            self.review_date.toordinal() if self.review_date else None,
            self.threshold_sort_value,
        )
        return values[column]

    def user_role_value(self, column: int) -> Any:
        if column == COL_REVIEW:
            return _to_qdate(self.review_date)
        return self.sort_value(column)

    def tooltip(self) -> str:
        position = self.position
        thesis_date = _parse_iso_date(position.initial_buy_date)
        thesis_date_text = (
            thesis_date.strftime("%d.%m.%Y") if thesis_date else "brak daty"
        )
        thesis_line = (
            f"Teza: {_format_money(position.initial_buy_price, position.currency)} "
            f"({thesis_date_text})"
        )
        average_line = (
            "Śr. koszt: "
            f"{_format_money(position.average_cost, position.currency, decimals=4)}"
        )

        if position.current_price is None:
            current_text = "Brak ceny"
        else:
            current_text = _format_money(position.current_price, position.currency)
        return_text = (
            _format_signed_pct(self.return_pct)
            if self.return_pct is not None
            else "Brak ceny"
        )
        current_line = f"Aktualna: {current_text} | Zwrot: {return_text}"

        gain_threshold = _format_signed_pct(position.sell_threshold_gain, 0)
        loss_threshold = _format_signed_pct(position.sell_threshold_loss, 0)
        targets_line = (
            f"Cele: ZAROBEK {gain_threshold} "
            f"({_format_money(self.snapshot.target_gain_price, position.currency)}) | "
            f"REALIZUJ {loss_threshold} "
            f"({_format_money(self.snapshot.target_loss_price, position.currency)})"
        )

        if self.snapshot.distance_to_gain_pct is None:
            gain_distance = "Brak ceny"
        else:
            gain_distance = _format_signed_pct(
                self.snapshot.distance_to_gain_pct
            )
        if self.snapshot.distance_to_loss_pct is None:
            loss_distance = "Brak ceny"
        else:
            loss_distance = _format_signed_pct(
                -abs(self.snapshot.distance_to_loss_pct)
            )
        distance_line = (
            f"Do ZAROBEK: {gain_distance} | Do REALIZUJ: {loss_distance}"
        )
        return "\n".join(
            (thesis_line, average_line, current_line, targets_line, distance_line)
        )


class PositionTableModel(QAbstractTableModel):
    """Eight-column dashboard model; missing values always sort last."""

    HEADERS = (
        "Ticker",
        "Nazwa",
        "Bieżąca",
        "Wartość",
        "Zwrot %",
        "Ocena",
        "Rewizja",
        "Do progu %",
    )

    HEADER_TOOLTIPS = (
        "Ticker instrumentu",
        "Nazwa spółki lub instrumentu",
        "Ostatnia ręcznie ustawiona cena rynkowa",
        "Bieżąca wartość posiadanych akcji",
        "Zwrot od średniego kosztu; dla zamkniętych zwrot zrealizowany",
        "Ocena według zdefiniowanych progów",
        "Termin najbliższej rewizji",
        "Odległość do odpowiedniego progu decyzyjnego",
    )

    PositionIdRole = int(Qt.ItemDataRole.UserRole) + 1
    PositionRole = int(Qt.ItemDataRole.UserRole) + 2

    def __init__(self, positions: list[Position] | None = None) -> None:
        super().__init__()
        self._rows = [PositionRow.from_position(item) for item in positions or []]
        self.positions = [row.position for row in self._rows]
        self._sort_column = COL_REVIEW
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._sort_rows()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if not 0 <= section < len(self.HEADERS):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        if role == Qt.ItemDataRole.ToolTipRole:
            return self.HEADER_TOOLTIPS[section]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        position = row.position
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return row.display_value(column)
        if role == Qt.ItemDataRole.UserRole:
            return row.user_role_value(column)
        if role == self.PositionIdRole:
            return position.id
        if role == self.PositionRole:
            return position
        if role == Qt.ItemDataRole.ToolTipRole:
            return row.tooltip()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column in {
                COL_CURRENT_PRICE,
                COL_MARKET_VALUE,
                COL_RETURN,
                COL_THRESHOLD_DISTANCE,
            }:
                return int(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            if column == COL_REVIEW:
                return int(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.BackgroundRole:
            style_key = (
                STATUS_CLOSED
                if position.status == STATUS_CLOSED
                else row.category or CATEGORY_NEUTRAL
            )
            style = CATEGORY_STYLES.get(
                style_key, CATEGORY_STYLES[CATEGORY_NEUTRAL]
            )
            return QColor(style["bg"])
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._foreground_for(row, column)
        if role == Qt.ItemDataRole.FontRole:
            font = QFont()
            if column in {COL_TICKER, COL_RETURN, COL_CATEGORY}:
                font.setBold(True)
            if column == COL_REVIEW and (
                row.review_days_delta is not None
                and row.review_days_delta <= 0
            ):
                font.setBold(True)
            if row.threshold_display in {"ZAROBEK", "REALIZUJ"} and (
                column == COL_THRESHOLD_DISTANCE
            ):
                font.setBold(True)
            if position.status == STATUS_CLOSED:
                font.setStrikeOut(True)
            return font
        return None

    @staticmethod
    def _foreground_for(row: PositionRow, column: int) -> QColor:
        position = row.position
        if position.status == STATUS_CLOSED:
            return QColor(CATEGORY_STYLES[STATUS_CLOSED]["fg"])
        if column == COL_RETURN and row.return_pct is not None:
            if row.return_pct > 0:
                return QColor(COLOR_POSITIVE)
            if row.return_pct < 0:
                return QColor(COLOR_NEGATIVE)
        if column == COL_REVIEW and row.review_days_delta is not None:
            if row.review_days_delta < 0:
                return QColor(COLOR_NEGATIVE)
            if row.review_days_delta == 0:
                return QColor(COLOR_TODAY)
        if column == COL_THRESHOLD_DISTANCE and row.threshold_color:
            return QColor(row.threshold_color)
        style_key = row.category or CATEGORY_NEUTRAL
        style = CATEGORY_STYLES.get(
            style_key, CATEGORY_STYLES[CATEGORY_NEUTRAL]
        )
        return QColor(style["fg"])

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        if not 0 <= column < len(self.HEADERS):
            return
        self._sort_column = column
        self._sort_order = order
        self.layoutAboutToBeChanged.emit()
        self._sort_rows()
        self.layoutChanged.emit()

    def _sort_rows(self) -> None:
        known: list[PositionRow] = []
        missing: list[PositionRow] = []
        for row in self._rows:
            destination = (
                missing
                if row.sort_value(self._sort_column) is None
                else known
            )
            destination.append(row)
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder
        known.sort(
            key=lambda row: row.sort_value(self._sort_column),
            reverse=reverse,
        )
        self._rows = known + missing
        self.positions = [row.position for row in self._rows]

    def set_positions(self, positions: list[Position]) -> None:
        self.beginResetModel()
        self._rows = [PositionRow.from_position(item) for item in positions]
        self._sort_rows()
        self.endResetModel()

    def position_at(self, row: int) -> Position | None:
        if 0 <= row < len(self._rows):
            return self._rows[row].position
        return None


class DashboardTable(QTableView):
    position_double_clicked = Signal(object)
    price_edit_requested = Signal(object)

    # Compatibility signals retained for the existing MainWindow wiring.
    positionDoubleClicked = Signal(object)
    contextMenuRequestedForPosition = Signal(object, QPoint)
    selectionChangedForPosition = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model_obj = PositionTableModel()
        self.setModel(self.model_obj)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(34)
        self.verticalHeader().setMinimumSectionSize(30)

        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setMinimumSectionSize(64)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(COL_TICKER, 82)
        self.setColumnWidth(COL_CURRENT_PRICE, 108)
        self.setColumnWidth(COL_MARKET_VALUE, 128)
        self.setColumnWidth(COL_RETURN, 88)
        self.setColumnWidth(COL_CATEGORY, 142)
        self.setColumnWidth(COL_REVIEW, 190)
        self.setColumnWidth(COL_THRESHOLD_DISTANCE, 110)

        self.doubleClicked.connect(self._handle_double_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.selectionModel().selectionChanged.connect(
            self._emit_selection_changed
        )
        self.sortByColumn(COL_REVIEW, Qt.SortOrder.AscendingOrder)

    def set_positions(self, positions: list[Position]) -> None:
        self.model_obj.set_positions(positions)
        if positions:
            self.selectRow(0)
        else:
            self.clearSelection()

    def selected_position(self) -> Position | None:
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.model_obj.position_at(indexes[0].row())

    def position_from_index(self, index: QModelIndex) -> Position | None:
        if not index.isValid():
            return None
        return self.model_obj.position_at(index.row())

    def _handle_double_clicked(self, index: QModelIndex) -> None:
        position = self.position_from_index(index)
        if position is None:
            return
        if index.column() == COL_CURRENT_PRICE:
            self.price_edit_requested.emit(position)
            self._invoke_window_handler(("set_market_price",), position)
            return
        self.position_double_clicked.emit(position)
        self.positionDoubleClicked.emit(position)

    def _open_context_menu(self, point: QPoint) -> None:
        index = self.indexAt(point)
        position = self.position_from_index(index)
        if position is None:
            return

        self.setCurrentIndex(index)

        menu = self.create_default_context_menu(position, self)
        selected = menu.exec(self.viewport().mapToGlobal(point))
        if selected is None:
            return
        action_name = selected.data()
        handlers = {
            "close": ("toggle_position_status",),
            "review": ("add_review",),
            "price": ("set_market_price",),
            "remove": ("remove_position", "delete_position"),
        }
        if action_name in handlers:
            self._invoke_window_handler(handlers[action_name], position)

    @staticmethod
    def create_default_context_menu(
        position: Position, parent: QWidget | None = None
    ) -> QMenu:
        menu = QMenu(parent)
        close_action = menu.addAction("Zamknij pozycję")
        close_action.setData("close")
        review_action = menu.addAction("Dodaj rewizję")
        review_action.setData("review")
        price_action = menu.addAction("Ustaw cenę rynkową")
        price_action.setData("price")
        menu.addSeparator()
        remove_action = menu.addAction("Usuń pozycję")
        remove_action.setData("remove")

        is_closed = position.status == STATUS_CLOSED
        close_action.setEnabled(not is_closed)
        review_action.setEnabled(not is_closed)
        price_action.setEnabled(not is_closed)
        return menu

    def _invoke_window_handler(
        self, method_names: tuple[str, ...], position: Position
    ) -> bool:
        window = self.window()
        for method_name in method_names:
            callback = getattr(window, method_name, None)
            if callable(callback):
                callback(position)
                return True
        return False

    def _emit_selection_changed(self, *_args: Any) -> None:
        self.selectionChangedForPosition.emit(self.selected_position())
