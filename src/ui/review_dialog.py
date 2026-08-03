from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    CATEGORY_STYLES,
    DISPLAY_DATE_FORMAT,
    METRIC_FIELDS,
    METRIC_LABELS,
    METRIC_UNITS,
    REVIEW_INTERVAL_DAYS,
)
from src.database import Database
from src.metrics_engine import (
    MetricTrend,
    compare_metric,
    describe_metric_change,
    get_trend_color,
    summarize_trends,
)
from src.models import Position, Review
from src.rule_engine import calculate_return, categorize_with_thresholds, format_return


def qdate_to_iso(value: QDate) -> str:
    return date(value.year(), value.month(), value.day()).isoformat()


def qdate_plus_days_iso(value: QDate, days: int) -> str:
    base = date(value.year(), value.month(), value.day())
    return (base + timedelta(days=days)).isoformat()


class ReviewDialog(QDialog):
    def __init__(
        self,
        database: Database,
        selected_position_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.database = database
        self.selected_position_id = selected_position_id
        self.positions: list[Position] = self.database.get_all_positions(
            include_closed=False
        )
        self.current_position: Position | None = None
        self.previous_review: Review | None = None
        self.metric_widgets: dict[str, dict[str, Any]] = {}
        self.last_result: dict[str, Any] | None = None
        self.setWindowTitle("Dodaj rewizję")
        self.setModal(True)
        self.resize(760, 720)
        self._build_ui()
        self._load_positions()
        self._connect_signals()
        self._select_initial_position()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        top_group = QGroupBox("Pozycja i cena")
        top_form = QFormLayout(top_group)
        self.position_combo = QComboBox()
        self.buy_price_label = QLabel("-")
        self.buy_price_label.setStyleSheet("color: #888888;")
        self.current_price_spin = QDoubleSpinBox()
        self.current_price_spin.setDecimals(4)
        self.current_price_spin.setRange(0.0001, 999999.99)
        self.current_price_spin.setSingleStep(0.1)
        self.review_date_edit = QDateEdit()
        self.review_date_edit.setCalendarPopup(True)
        self.review_date_edit.setDisplayFormat(DISPLAY_DATE_FORMAT)
        self.review_date_edit.setDate(QDate.currentDate())
        top_form.addRow("Spółka", self.position_combo)
        top_form.addRow("Cena zakupu", self.buy_price_label)
        top_form.addRow("Aktualna cena", self.current_price_spin)
        top_form.addRow("Data rewizji", self.review_date_edit)
        main_layout.addWidget(top_group)

        metrics_group = QGroupBox("Metryki fundamentalne")
        metrics_layout = QGridLayout(metrics_group)
        metrics_layout.setColumnStretch(1, 1)
        for row, metric_name in enumerate(METRIC_FIELDS):
            name_label = QLabel(METRIC_LABELS[metric_name])
            name_label.setMinimumWidth(150)
            name_font = QFont()
            name_font.setBold(True)
            name_label.setFont(name_font)

            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(-1.0, 9999.0)
            spin.setSpecialValueText("brak")
            spin.setValue(-1.0)
            spin.setSingleStep(0.1)
            spin.setMinimumWidth(110)
            unit_label = QLabel(METRIC_UNITS.get(metric_name, ""))
            previous_label = QLabel("poprzednio: brak")
            previous_label.setStyleSheet("color: #888888;")
            trend_label = QLabel("●")
            trend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            trend_label.setMinimumWidth(42)
            desc_label = QLabel(" (bez zmian)")
            desc_label.setStyleSheet("color: #888888;")

            metrics_layout.addWidget(name_label, row, 0)
            metrics_layout.addWidget(spin, row, 1)
            metrics_layout.addWidget(unit_label, row, 2)
            metrics_layout.addWidget(previous_label, row, 3)
            metrics_layout.addWidget(trend_label, row, 4)
            metrics_layout.addWidget(desc_label, row, 5)
            self.metric_widgets[metric_name] = {
                "spin": spin,
                "previous_label": previous_label,
                "trend_label": trend_label,
                "desc_label": desc_label,
            }

        main_layout.addWidget(metrics_group)

        self.calculate_button = QPushButton("Oblicz")
        self.calculate_button.setDefault(True)
        main_layout.addWidget(self.calculate_button)

        self.result_frame = QFrame()
        self.result_frame.setObjectName("ResultFrame")
        result_layout = QVBoxLayout(self.result_frame)
        self.return_label = QLabel("Zwrot: –")
        self.return_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.return_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.category_label = QLabel("Kategoria: –")
        self.category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.category_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self.instruction_label = QLabel("Instrukcja: –")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label = QLabel(
            "Metryki polepszone: 0 / pogorszone: 0 / bez zmian: 0"
        )
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.return_label)
        result_layout.addWidget(self.category_label)
        result_layout.addWidget(self.instruction_label)
        result_layout.addWidget(self.summary_label)
        main_layout.addWidget(self.result_frame)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Notatki z rewizji, decyzja, kontekst fundamentalny..."
        )
        self.notes_edit.setMinimumHeight(110)
        main_layout.addWidget(QLabel("Notatki"))
        main_layout.addWidget(self.notes_edit, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        self.save_button = QPushButton("Zapisz rewizję")
        self.save_button.setEnabled(False)
        self.cancel_button = QPushButton("Anuluj")
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(buttons_layout)

    def _connect_signals(self) -> None:
        self.position_combo.currentIndexChanged.connect(self._load_selected_position)
        self.calculate_button.clicked.connect(self._calculate)
        self.save_button.clicked.connect(self._save)
        self.cancel_button.clicked.connect(self.reject)
        self.current_price_spin.valueChanged.connect(self._mark_dirty)
        self.review_date_edit.dateChanged.connect(self._mark_dirty)
        for widgets in self.metric_widgets.values():
            widgets["spin"].valueChanged.connect(self._mark_dirty)

    def _load_positions(self) -> None:
        self.position_combo.clear()
        for position in self.positions:
            self.position_combo.addItem(
                f"{position.ticker} – {position.name}", position.id
            )
        if not self.positions:
            self.position_combo.addItem("Brak otwartych pozycji", None)
            self.calculate_button.setEnabled(False)

    def _select_initial_position(self) -> None:
        if self.selected_position_id is not None:
            for index in range(self.position_combo.count()):
                if self.position_combo.itemData(index) == self.selected_position_id:
                    self.position_combo.setCurrentIndex(index)
                    break
        self._load_selected_position()
        self.current_price_spin.setFocus(Qt.FocusReason.OtherFocusReason)

    def _load_selected_position(self) -> None:
        position_id = self.position_combo.currentData()
        self.current_position = (
            self.database.get_position_by_id(int(position_id)) if position_id else None
        )
        if self.current_position is None:
            self.buy_price_label.setText("–")
            return

        position = self.current_position
        self.buy_price_label.setText(f"{position.buy_price:.4f} {position.currency}")
        self.current_price_spin.setValue(position.display_price())
        self.previous_review = self.database.get_last_review_for_position(
            position.id or 0
        )
        self._load_previous_metrics()
        self._mark_dirty()

    def _load_previous_metrics(self) -> None:
        for metric_name, widgets in self.metric_widgets.items():
            previous = (
                self.previous_review.metric_value(metric_name)
                if self.previous_review is not None
                else None
            )
            if previous is None:
                widgets["previous_label"].setText("poprzednio: brak")
            else:
                widgets["previous_label"].setText(
                    f"poprzednio: {previous:.2f}{METRIC_UNITS.get(metric_name, '')}"
                )
            widgets["trend_label"].setText("●")
            widgets["trend_label"].setStyleSheet("color: #888888;")
            widgets["desc_label"].setText(" (bez zmian)")

    def _metric_value(self, metric_name: str) -> float | None:
        spin = self.metric_widgets[metric_name]["spin"]
        value = float(spin.value())
        return None if value < 0 else value

    def _metric_values(self) -> dict[str, float | None]:
        return {
            metric_name: self._metric_value(metric_name)
            for metric_name in METRIC_FIELDS
        }

    def _mark_dirty(self) -> None:
        self.last_result = None
        self.save_button.setEnabled(False)

    def _calculate(self) -> None:
        if self.current_position is None:
            QMessageBox.warning(
                self, "Brak pozycji", "Najpierw wybierz otwartą pozycję."
            )
            return
        position = self.current_position
        try:
            return_pct = calculate_return(
                position.buy_price, self.current_price_spin.value()
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Błąd obliczeń", str(exc))
            return
        category, instruction = categorize_with_thresholds(
            return_pct,
            position.sell_threshold_gain,
            position.sell_threshold_profit,
            position.sell_threshold_loss,
        )
        metric_values = self._metric_values()
        trends: dict[str, MetricTrend] = {}
        for metric_name, current in metric_values.items():
            previous = (
                self.previous_review.metric_value(metric_name)
                if self.previous_review is not None
                else None
            )
            trend = compare_metric(metric_name, current, previous)
            trends[metric_name] = trend
            color, emoji = get_trend_color(trend)
            desc = describe_metric_change(metric_name, current, previous)
            self.metric_widgets[metric_name]["trend_label"].setText(emoji)
            self.metric_widgets[metric_name]["trend_label"].setStyleSheet(
                f"color: {color}; font-size: 13pt;"
            )
            self.metric_widgets[metric_name]["desc_label"].setText(f"({desc})")

        summary = summarize_trends(trends)
        style = CATEGORY_STYLES.get(category, CATEGORY_STYLES["NEUTRALNY"])
        self.result_frame.setStyleSheet(
            f"QFrame#ResultFrame {{ background-color: {style['bg']}; border: 1px solid #4A4A4A; border-radius: 6px; }}"
        )
        self.return_label.setText(f"Zwrot: {format_return(return_pct)}")
        self.category_label.setText(f"{category}")
        self.category_label.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {style['fg']};"
        )
        icon = "⚠️" if instruction == "SPRZEDAJ" else "✅"
        self.instruction_label.setText(f"Instrukcja: {icon} {instruction}")
        self.summary_label.setText(
            "Metryki polepszone: "
            f"{summary[MetricTrend.IMPROVED]} / pogorszone: {summary[MetricTrend.WORSENED]} / "
            f"bez zmian: {summary[MetricTrend.UNCHANGED]}"
        )

        self.last_result = {
            "return_pct": return_pct,
            "category": category,
            "instruction": instruction,
            "metric_values": metric_values,
        }
        self.save_button.setEnabled(True)

    def _save(self) -> None:
        if self.current_position is None:
            QMessageBox.warning(self, "Brak pozycji", "Nie wybrano pozycji do rewizji.")
            return
        if self.last_result is None:
            self._calculate()
        if self.last_result is None:
            return

        position = self.current_position
        metric_values = self.last_result["metric_values"]
        review = Review(
            position_id=position.id or 0,
            review_date=qdate_to_iso(self.review_date_edit.date()),
            price_then=self.current_price_spin.value(),
            return_pct=self.last_result["return_pct"],
            category=self.last_result["category"],
            instruction=self.last_result["instruction"],
            pe_ratio=metric_values["pe_ratio"],
            dividend_yield=metric_values["dividend_yield"],
            debt_to_equity=metric_values["debt_to_equity"],
            roe=metric_values["roe"],
            payout_ratio=metric_values["payout_ratio"],
            revenue_growth_3y=metric_values["revenue_growth_3y"],
            notes=self.notes_edit.toPlainText().strip() or None,
        )
        try:
            self.database.insert_review(review)
            self.database.update_position_after_review(
                position.id or 0,
                self.current_price_spin.value(),
                qdate_plus_days_iso(self.review_date_edit.date(), REVIEW_INTERVAL_DAYS),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Błąd zapisu", str(exc))
            return
        self.accept()
