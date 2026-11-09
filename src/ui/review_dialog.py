

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
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
    QScrollArea,
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
    review_metric_source,
    sources_comparable,
)
from src.fundamentals import available_on, canonical, series_signature
from src.ui.fundamentals_dialog import FundamentalsDialog
from src.models import Position, PositionValuation, Review
from src.rule_engine import categorize_with_thresholds, format_return


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
        self.evidence_records: list[dict] = []
        self.bindings: dict[str, int] = {}
        self.imported_values: dict[str, float | None] = {}
        self.setWindowTitle("Dodaj rewizję")
        self.setModal(True)
        self.resize(950, 820)
        self._build_ui()
        self._load_positions()
        self._connect_signals()
        self._select_initial_position()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        main_layout = QVBoxLayout(body)
        scroll.setWidget(body)
        outer_layout.addWidget(scroll)

        top_group = QGroupBox("Pozycja i cena")
        top_form = QFormLayout(top_group)
        self.position_combo = QComboBox()
        self.average_cost_label = QLabel("-")
        self.average_cost_label.setStyleSheet("color: #888888;")
        self.current_price_spin = QDoubleSpinBox()
        self.current_price_spin.setDecimals(4)
        self.current_price_spin.setRange(0.0, 999999.99)
        self.current_price_spin.setSpecialValueText("wpisz cenę")
        self.current_price_spin.setSingleStep(0.1)
        self.review_date_edit = QDateEdit()
        self.review_date_edit.setCalendarPopup(True)
        self.review_date_edit.setDisplayFormat(DISPLAY_DATE_FORMAT)
        self.review_date_edit.setDate(QDate.currentDate())
        self.review_date_edit.setMaximumDate(QDate.currentDate())
        top_form.addRow("Spółka", self.position_combo)
        top_form.addRow("Średni koszt", self.average_cost_label)
        top_form.addRow("Aktualna cena", self.current_price_spin)
        top_form.addRow("Data rzeczywistej analizy", self.review_date_edit)
        main_layout.addWidget(top_group)
        date_hint = QLabel("Data analizy nie jest datą zakupu ani okresem raportu. Historyczne dane nie tworzą dawnych rewizji.")
        date_hint.setWordWrap(True)
        main_layout.addWidget(date_hint)
        self.fundamental_button = QPushButton("Historia spółki / import JSON / wybór danych…")
        self.fundamental_button.clicked.connect(self._choose_fundamentals)
        main_layout.addWidget(self.fundamental_button)
        self.evidence_label = QLabel("Dane ręczne — pochodzenie i okres nieustalone.")
        self.evidence_label.setWordWrap(True)
        main_layout.addWidget(self.evidence_label)

        metrics_group = QGroupBox("Metryki przy rzeczywistych rewizjach — porównanie z poprzednią analizą")
        metrics_layout = QGridLayout(metrics_group)
        metrics_layout.setColumnStretch(1, 1)
        for row, metric_name in enumerate(METRIC_FIELDS):
            name_label = QLabel(METRIC_LABELS[metric_name])
            name_label.setMinimumWidth(150)
            name_font = QFont()
            name_font.setBold(True)
            name_label.setFont(name_font)

            spin = QDoubleSpinBox()
            spin.setDecimals(8)
            spin.setRange(-1e15, 1e15)
            missing = QCheckBox("brak")
            missing.setChecked(True)
            spin.setEnabled(False)
            missing.toggled.connect(lambda checked, s=spin: s.setEnabled(not checked))
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
            entry = QHBoxLayout()
            entry.addWidget(spin)
            entry.addWidget(missing)
            metrics_layout.addLayout(entry, row, 1)
            metrics_layout.addWidget(unit_label, row, 2)
            metrics_layout.addWidget(previous_label, row, 3)
            metrics_layout.addWidget(trend_label, row, 4)
            metrics_layout.addWidget(desc_label, row, 5)
            self.metric_widgets[metric_name] = {
                "spin": spin,
                "missing": missing,
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
        self.summary_label.setWordWrap(True)
        result_layout.addWidget(self.return_label)
        result_layout.addWidget(self.category_label)
        result_layout.addWidget(self.instruction_label)
        result_layout.addWidget(self.summary_label)
        main_layout.addWidget(self.result_frame)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Dzisiejsza teza, ocena, ryzyka i decyzja. Powody dawnego zakupu opisuj jako późniejsze wspomnienie, jeżeli nie masz dawnych notatek."
        )
        self.notes_edit.setMinimumHeight(110)
        self.previous_notes = QTextEdit()
        self.previous_notes.setReadOnly(True)
        self.previous_notes.setMaximumHeight(100)
        main_layout.addWidget(QLabel("Ocena inwestora: poprzednia rzeczywista rewizja"))
        main_layout.addWidget(self.previous_notes)
        main_layout.addWidget(QLabel("Ocena inwestora i decyzja w tej rewizji (kategoria powyżej jest automatyczna)"))
        main_layout.addWidget(self.notes_edit, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        self.save_button = QPushButton("Zapisz rewizję")
        self.save_button.setEnabled(False)
        self.cancel_button = QPushButton("Anuluj")
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        outer_layout.addLayout(buttons_layout)

    def _connect_signals(self) -> None:
        self.position_combo.currentIndexChanged.connect(self._load_selected_position)
        self.calculate_button.clicked.connect(self._calculate)
        self.save_button.clicked.connect(self._save)
        self.cancel_button.clicked.connect(self.reject)
        self.current_price_spin.valueChanged.connect(self._mark_dirty)
        self.review_date_edit.dateChanged.connect(self._mark_dirty)
        self.review_date_edit.dateChanged.connect(self._refresh_previous_review)
        for widgets in self.metric_widgets.values():
            widgets["spin"].valueChanged.connect(self._mark_dirty)
            widgets["missing"].toggled.connect(self._mark_dirty)

    def _load_positions(self) -> None:
        self.position_combo.clear()
        for position in self.positions:
            self.position_combo.addItem(
                f"{position.ticker} – {position.name or 'brak nazwy'}", position.id
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

    def _load_selected_position(self, _index: int = -1) -> None:
        position_id = self.position_combo.currentData()
        self.current_position = (
            self.database.get_position_by_id(int(position_id)) if position_id else None
        )
        if self.current_position is None:
            self.average_cost_label.setText("–")
            self.current_price_spin.setValue(0.0)
            return

        position = self.current_position
        self.average_cost_label.setText(
            f"{position.average_cost:.4f} {position.currency}"
        )
        self.current_price_spin.setValue(position.current_price or 0.0)
        self.previous_review = self.database.get_last_review_for_position(
            position.id or 0
        )
        self.notes_edit.clear()
        self.evidence_records = []
        self.bindings = {}
        self.imported_values = {}
        self.evidence_label.setText("Dane ręczne — pochodzenie i okres nieustalone.")
        self.previous_notes.setPlainText(
            f"{self.previous_review.review_date}\n{self.previous_review.notes or 'Brak notatek oceny inwestora.'}"
            if self.previous_review else "Brak wcześniejszej rzeczywistej rewizji.")
        self._load_previous_metrics()
        self._mark_dirty()

    def _load_previous_metrics(self) -> None:
        for metric_name, widgets in self.metric_widgets.items():
            widgets["spin"].setValue(0)
            widgets["missing"].setChecked(True)
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
            widgets["desc_label"].setText(" (brak porównania)")

    def _metric_value(self, metric_name: str) -> float | None:
        spin = self.metric_widgets[metric_name]["spin"]
        if self.metric_widgets[metric_name]["missing"].isChecked():
            return None
        value = float(spin.value())
        imported = self.imported_values.get(metric_name)
        if imported is not None and value == round(imported, 8):
            return imported
        return value

    def _choose_fundamentals(self) -> None:
        if self.current_position is None:
            return
        dialog = FundamentalsDialog(self.database, self.current_position.isin,
            qdate_to_iso(self.review_date_edit.date()), choose=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.apply_fundamental_records(dialog.selected_records)
            except ValueError as exc:
                QMessageBox.warning(self, "Wybór danych", str(exc))

    def apply_fundamental_records(self, records: list[dict]) -> None:
        reviewed_on = qdate_to_iso(self.review_date_edit.date())
        if any(not available_on(r["observation"], reviewed_on) for r in records):
            raise ValueError("Dane nie były dostępne w dniu rzeczywistej analizy.")
        if len({r["logical_key"] for r in records}) != len(records):
            raise ValueError("Wybierz jedną wersję korekty dla danego okresu i metryki.")
        selected = {}
        for name in METRIC_FIELDS:
            items = [r for r in records if r["observation"]["metric"] == name]
            if len({series_signature(r) for r in items}) > 1:
                raise ValueError(f"{METRIC_LABELS[name]}: wybierz jedną definicję, zakres i podstawę okresu.")
            if items:
                selected[name] = max(items, key=lambda r: (r["observation"]["valuation_date"] or r["observation"]["period"]["end"], r["id"]))
        self.evidence_records = records
        self.bindings = {name: r["id"] for name, r in selected.items()}
        self.imported_values = {name: r["observation"]["value"] for name, r in selected.items()}
        for name, r in selected.items():
            value = r["observation"]["value"]
            self.metric_widgets[name]["missing"].setChecked(value is None)
            self.metric_widgets[name]["spin"].setValue(value if value is not None else 0)
        periods = sorted({r["observation"]["period"]["end"] for r in records})
        self.evidence_label.setText(f"Dołączono {len(records)} obserwacji. Okresy: {', '.join(periods)}. Najnowsze wybrane wartości wypełniły pola; ręczne zmiany będą oznaczone.")
        self._mark_dirty()

    def _metric_values(self) -> dict[str, float | None]:
        return {
            metric_name: self._metric_value(metric_name)
            for metric_name in METRIC_FIELDS
        }

    def _refresh_previous_review(self, *_args) -> None:
        if self.current_position is None:
            return
        earlier = [r for r in self.database.get_reviews_for_position(self.current_position.id or 0)
                   if r.review_date <= qdate_to_iso(self.review_date_edit.date())]
        self.previous_review = earlier[0] if earlier else None
        self.previous_notes.setPlainText(
            f"{self.previous_review.review_date}\n{self.previous_review.notes or 'Brak notatek.'}"
            if self.previous_review else "Brak wcześniejszej rzeczywistej rewizji.")
        for name, widgets in self.metric_widgets.items():
            value = self.previous_review.metric_value(name) if self.previous_review else None
            widgets["previous_label"].setText(f"poprzednio: {value if value is not None else 'brak'}")

    def _mark_dirty(self, *_args: Any) -> None:
        self.last_result = None
        self.save_button.setEnabled(False)

    def _calculate(self) -> None:
        if self.current_position is None:
            QMessageBox.warning(
                self, "Brak pozycji", "Najpierw wybierz otwartą pozycję."
            )
            return
        position = self.current_position
        if any(not available_on(r["observation"], qdate_to_iso(self.review_date_edit.date())) for r in self.evidence_records):
            QMessageBox.warning(self, "Dane późniejsze niż analiza", "Zmień wybór danych albo podaj właściwą datę rzeczywistej analizy.")
            return
        self._refresh_previous_review()
        current_price = self.current_price_spin.value()
        if current_price <= 0:
            QMessageBox.warning(
                self,
                "Brak ceny",
                "Wpisz aktualną cenę rynkową większą od zera.",
            )
            return
        snapshot = PositionValuation.snapshot(
            replace(position, current_price=current_price)
        )
        return_pct = snapshot.unrealized_return
        if return_pct is None:
            QMessageBox.warning(
                self,
                "Błąd wyceny",
                "Nie można wyliczyć zwrotu dla tej pozycji.",
            )
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
            current_source = next((r for r in self.evidence_records if r["id"] == self.bindings.get(metric_name) and r["observation"]["value"] == current), None)
            if not sources_comparable(current_source, review_metric_source(self.previous_review, metric_name)):
                trend = MetricTrend.NO_DATA
            trends[metric_name] = trend
            color, emoji = get_trend_color(trend)
            desc = "brak porównania" if trend == MetricTrend.NO_DATA else describe_metric_change(metric_name, current, previous)
            self.metric_widgets[metric_name]["previous_label"].setText(f"poprzednio: {previous if previous is not None else 'brak'}")
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
            f"bez zmian: {summary[MetricTrend.UNCHANGED]} / brak porównania: {summary[MetricTrend.NO_DATA]}. Ręczne definicje niezweryfikowane."
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
        if self.review_date_edit.date() != QDate.currentDate():
            answer = QMessageBox.question(self, "Data wcześniejszej analizy",
                "Czy analiza została rzeczywiście wykonana w podanym dniu? Historyczne dane spółki same nie uzasadniają wcześniejszej daty rewizji.\n\nZwrot nadal korzysta z bieżącego średniego kosztu pozycji. Aplikacja nie odtwarza historycznego stanu posiadania.")
            if answer != QMessageBox.StandardButton.Yes:
                return
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
            fundamental_evidence_json=canonical({"observation_ids": [r["id"] for r in self.evidence_records], "bindings": self.bindings}),
        )
        try:
            self.database.insert_review_and_update_position(
                review,
                self.current_price_spin.value(),
                qdate_plus_days_iso(self.review_date_edit.date(), REVIEW_INTERVAL_DAYS),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Błąd zapisu", str(exc))
            return
        self.accept()

