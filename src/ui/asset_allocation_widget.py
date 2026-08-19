from __future__ import annotations
from dataclasses import replace
from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtCharts import QChart, QChartView, QPieSeries
except ImportError:
    QChart = None
    QChartView = None
    QPieSeries = None

from src.asset_engine import (
    format_pct,
    get_rebalance_delta,
    recalculate_actual_allocation,
)
from src.database import Database
from src.models import AssetCategory


class AssetTilesWidget(QWidget):
    ICONS = {
        "akcje": "🟦",
        "obligacje": "🟩",
        "złoto": "🟨",
        "lokaty": "🟪",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.categories: list[AssetCategory] = []
        self.actual: dict[str, float] = {}
        self.delta: dict[str, float] = {}
        self.hover_index: int = -1
        self.setMouseTracking(True)
        self.setMinimumHeight(360)

    def set_data(
        self,
        categories: list[AssetCategory],
        actual: dict[str, float],
        delta: dict[str, float],
    ) -> None:
        self.categories = categories
        self.actual = actual
        self.delta = delta
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(720, 420)

    def mouseMoveEvent(self, event: Any) -> None:
        old = self.hover_index
        self.hover_index = -1
        for index, rect in enumerate(self.tile_rects()):
            if rect.contains(event.position().toPoint()):
                self.hover_index = index
                break
        if old != self.hover_index:
            self.update()

    def leaveEvent(self, event: Any) -> None:
        self.hover_index = -1
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#2E2E2E"))
        painter.fillRect(self.rect(), QColor("#2A2A2A"))
        rects = self.tile_rects()
        for index, (category, rect) in enumerate(zip(self.categories, rects)):
            self._draw_tile(painter, category, rect, index == self.hover_index)

    def tile_rects(self) -> list[QRect]:
        count = max(len(self.categories), 1)
        columns = 2 if count == 1 else 2
        rows = count // columns + (count % columns > 0)
        spacing = 12
        margin = 10
        tile_width = max(
            120, (self.width() - 2 * margin - (columns - 1) * spacing) // columns
        )
        tile_height = max(
            120, (self.height() - 2 * margin - (rows - 1) * spacing) // rows
        )
        rects: list[QRect] = []
        for index in range(count):
            col = index % columns
            row = index // columns
            x = margin + col * (tile_width + spacing)
            y = margin + row * (tile_height + spacing)
            rects.append(QRect(x, y, tile_width, tile_height))
        return rects

    def _draw_tile(
        self, painter: QPainter, category: AssetCategory, rect: QRect, hover: bool
    ) -> None:
        path = QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#3D3D3D") if hover else QColor("#404040"))
        painter.drawPath(path)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(rect.adjusted(10, 10, -10, -10), Qt.AlignTop, category.name)
        painter.setPen(QColor("#A4A4A4") if hover else QColor("#A4A4A4"))
        painter.drawText(
            rect.adjusted(10, 25, -10, -10),
            Qt.AlignTop,
            f"{format_pct(category.allocation * 100)}%",
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#3DAEEF") if hover else QColor("#4AA4FF"))
        percentage = category.allocation * 100
        rect_width = int(rect.width() * (percentage / 100))
        rect_height = 4
        x = rect.x() + 5
        y = rect.bottom() - 10 - rect_height
        painter.drawRect(x, y, rect_width, rect_height)
        painter.drawPath(path)


class TargetEditDialog(QDialog):
    def __init__(
        self, categories: list[AssetCategory], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.categories = categories
        self.spins: dict[int, QDoubleSpinBox] = {}
        self.setWindowTitle("Edytuj targety alokacji")
        self.setModal(True)
        self.resize(420, 300)
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        for row, category in enumerate(categories):
            label = QLabel(category.name)
            spin = QDoubleSpinBox()
            spin.setMaximum(100.0)
            spin.setSuffix("%")
            spin.setValue(category.target_pct * 100)
            spin.valueChanged.connect(lambda value, row=row: self.update_total(row))
            grid.addWidget(label, row, 0)
            grid.addWidget(spin, row, 1)
            self.spins[category.id] = spin
        layout.addLayout(grid)
        self.lbl_total = QLabel("Suma targetów: 0.00%")
        layout.addWidget(self.lbl_total)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_save = button_box.button(QDialogButtonBox.StandardButton.Save)
        self.btn_save.setText("Zapisz")
        self.btn_cancel = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.btn_cancel.setText("Anuluj")
        layout.addWidget(button_box)
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def update_total(self, row: int) -> None:
        total = sum(spin.value() for spin in self.spins.values())
        self.lbl_total.setText(f"Suma targetów: {total:.2f}%")
        if total > 100.0:
            self.lbl_total.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.lbl_total.setStyleSheet("color: None;")

    def accept(self) -> None:
        if sum(spin.value() for spin in self.spins.values()) != 100.0:
            QMessageBox.warning(self, "Błąd", "Suma targetów musi wynosić 100%.")
            return
        super().accept()

    def updated_categories(self) -> list[AssetCategory]:
        result: list[AssetCategory] = []
        for category in self.categories:
            new_pct = self.spins[category.id].value() / 100
            if abs(category.target_pct - new_pct) > 1e-6:
                category = replace(category, target_pct=new_pct)
                result.append(category)
        return result


class AssetAllocationWidget(QWidget):
    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.database = database
        self.categories: list[AssetCategory] = []
        self.actual: dict[str, float] = {}
        self.delta: dict[str, float] = {}
        self.setMinimumSize(760, 560)
        self.refresh()

    def build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_chart_tab(), "Podział portfela")
        self.tabs.addTab(self.build_tiles_tab(), "Strategiczny przegląd")
        layout.addWidget(self.tabs)

    def build_chart_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        if QChart is not None and QChartView is not None and QPieSeries is not None:
            self.series = QPieSeries()
            self.series.append("Asset allocation")
            self.series.setLabelsVisible(True)
            self.series.setLabelsPosition(QPieSeries.LabelsPosition.Outside)
            self.chart = QChart()
            self.chart.addSeries(self.series)
            self.chart.setBackgroundVisible(False)
            self.chart.setTheme(QChart.ChartTheme.Dark)
            self.chart.legend().setLabelColor(QColor("#CCCCCC"))
            self.chart_view = QChartView(self.chart)
            self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            layout.addWidget(self.chart_view, 1)
        else:
            layout.addWidget(
                QLabel("PySide6.QtCharts nie jest dostępne w tej instalacji."), 1
            )
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ("Kategoria", "Target %", "Actual %", "Delta")
        )
        layout.addWidget(self.table)
        button_box = QHBoxLayout()
        self.btn_edit_targets = QPushButton("Edytuj targety")
        button_box.addWidget(self.btn_edit_targets)
        self.btn_edit_targets.clicked.connect(self.edit_targets)
        self.btn_refresh = QPushButton("Odśwież")
        button_box.addWidget(self.btn_refresh)
        self.btn_refresh.clicked.connect(self.refresh)
        layout.addLayout(button_box)
        return tab

    def build_tiles_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.tiles = AssetTilesWidget()
        layout.addWidget(self.tiles)
        return tab

    def refresh(self) -> None:
        self.categories = self.database.get_all_asset_categories()
        positions = self.database.get_all_positions(include_closed=False)
        self.actual = recalculate_actual_allocation(positions)
        target = {category.name: category.target_pct for category in self.categories}
        self.delta = get_rebalance_delta(target, self.actual)
        self.refresh_chart()
        self.tiles.set_data(self.categories, self.actual, self.delta)

    def refresh_chart(self) -> None:
        if not hasattr(self, "series") or self.series is None:
            return
        self.series.clear()
        for category in self.categories:
            value = self.actual.get(category.name, category.actual_pct)
            if value < 0:
                continue
            pie_slice = self.series.append(
                f"{category.name} {format_pct(value)}", value
            )
            pie_slice.setLabelVisible(True)
            pie_slice.setLabelColor(QColor("#CCCCCC"))
        self.chart.update()

    def refresh_table(self) -> None:
        self.table.setRowCount(len(self.categories))
        for row, category in enumerate(self.categories):
            actual = self.actual.get(category.name, category.actual_pct)
            delta = self.delta.get(category.name, category.target_pct - actual)
            values = (
                category.name,
                format_pct(category.target_pct),
                format_pct(actual),
                format_pct(delta),
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in (1, 2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if col == 3:
                    item.setForeground(QColor("#90EE90" if delta >= 0 else "#FF6B6B"))
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()

    def edit_targets(self) -> None:
        dialog = TargetEditDialog(self.categories, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                for category in dialog.updated_categories():
                    self.database.update_asset_category(category)
            except Exception as exc:
                QMessageBox.critical(self, "Błąd targetów", str(exc))
                return
        self.refresh()
