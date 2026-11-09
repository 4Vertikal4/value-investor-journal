from __future__ import annotations

import json
import sqlite3
from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDialog, QFileDialog,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from src.config import METRIC_LABELS
from src.database import Database
from src.fundamentals import available_on, read_package, series_signature
from src.metrics_engine import fundamental_change


def observation_text(record: dict) -> str:
    o = record["observation"]
    source, period = o["source"], o["period"]
    return "\n".join([
        f"Emitent: {record['issuer']['name']}",
        f"Metryka: {METRIC_LABELS.get(o['metric'], o['metric'])}",
        f"Zakres: {o['scope']} / ISIN: {o['isin'] or 'dane całej spółki'}",
        f"Okres: {period['start']} – {period['end']} ({period['basis']})",
        f"Udostępniono tę wersję: {o['published_on'] or 'nieustalone'}",
        f"Data wyceny: {o['valuation_date'] or 'nie dotyczy'}",
        f"Wartość: {o['value'] if o['value'] is not None else 'brak'} {o['unit']} / {o['currency'] or 'bez waluty'}",
        f"Definicja: {o['definition']}", f"Obliczenie: {o['calculation'] or 'wartość podana w źródle'}",
        f"Źródło: {source['name']}\n{source['url']}\nStrona/tabela: {source['locator'] or 'nie podano'}",
        f"Brak danych: {o['missing_reason'] or 'nie dotyczy'}",
        f"Niepewność: {o['uncertainty'] or 'nie zgłoszono; nadal wymaga weryfikacji'}",
    ])


def fill_table(table: QTableWidget, records: list[dict], actions: list[str] | None = None) -> None:
    table.setColumnCount(10)
    table.setHorizontalHeaderLabels([
        "Metryka", "Zakres / ISIN", "Okres", "Udostępniono", "Wycena",
        "Wartość", "Jednostka / waluta", "Definicja", "Źródło", "Status / zmiana okresowa",
    ])
    table.setRowCount(len(records))
    predecessors = {}
    if actions is None:
        groups = {}
        for record in records:
            groups.setdefault(series_signature(record), []).append(record)
        for signature, items in groups.items():
            by_period = {}
            for record in sorted(items, key=lambda r: r.get("id", 0)):
                by_period[record["observation"]["period"]["end"]] = record
            previous = None
            for end in sorted(by_period):
                predecessors[(signature, end)] = previous
                previous = by_period[end]
    for row, record in enumerate(records):
        o, p = record["observation"], record["observation"]["period"]
        previous = predecessors.get((series_signature(record), p["end"]))
        text = actions[row] if actions is not None else fundamental_change(record, previous)
        tooltip = observation_text(record)
        values = [METRIC_LABELS.get(o["metric"], o["metric"]),
                  "spółka" if o["scope"] == "company" else o["isin"],
                  f"{p['start']} – {p['end']} ({p['basis']})", o["published_on"] or "NIEZNANA",
                  o["valuation_date"] or "—", "brak" if o["value"] is None else f"{o['value']:.10g}",
                  f"{o['unit']} / {o['currency'] or '—'}", o["definition"], o["source"]["name"], text]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setToolTip(tooltip)
            table.setItem(row, col, item)
    table.resizeColumnsToContents()
    # Long definitions and URLs remain accessible in the details pane.
    for col in (2, 7, 8, 9):
        table.setColumnWidth(col, min(table.columnWidth(col), 280))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)


class FundamentalImportDialog(QDialog):
    """Constructing/closing a preview never writes to the journal."""
    def __init__(self, database: Database, path: str, parent: QWidget | None = None,
                 expected_isin: str | None = None) -> None:
        super().__init__(parent)
        self.database = database
        self.package = read_package(path)
        if expected_isin and expected_isin not in {i["isin"] for i in self.package["instruments"]}:
            raise ValueError("Pakiet nie zawiera ISIN pozycji wybranej do rewizji.")
        plan = database.fundamentals.preview(self.package)
        self.preview_token = plan.token
        self.setWindowTitle("Podgląd importu danych fundamentalnych — bez tworzenia rewizji")
        self.resize(1150, 750)
        layout = QVBoxLayout(self)
        header = QLabel()
        header.setTextFormat(Qt.TextFormat.PlainText)
        header.setText(f"Emitent: {self.package['issuer']['name']} ({self.package['issuer']['id']})\n" +
                       "\n".join(plan.mapping_notes) + f"\nNowe: {plan.counts['new']}, korekty: {plan.counts['correction']}, powtórzenia: {plan.counts['duplicate']}.")
        header.setWordWrap(True)
        layout.addWidget(header)
        self.records = [{"issuer": self.package["issuer"], "observation": r["observation"]} for r in plan.rows]
        self.table = QTableWidget()
        fill_table(self.table, self.records, [{"new": "NOWA", "duplicate": "powtórzenie — pominięcie", "correction": "KOREKTA — nowa wersja"}[r["action"]] for r in plan.rows])
        layout.addWidget(self.table, 1)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(200)
        layout.addWidget(self.details)
        self.table.itemSelectionChanged.connect(self._details)
        self.confirm = QCheckBox("Sprawdziłem emitenta, klasy akcji, źródła i wskazane korekty. Zatwierdzam zapis.")
        layout.addWidget(self.confirm)
        if any(r["observation"]["published_on"] is None for r in self.records):
            warning = QLabel(
                "W pakiecie są obserwacje z nieustaloną datą udostępnienia. "
                "Można je zachować, ale nie użyć w datowanej rewizji. "
                "Import nie zmienia pozycji ani terminu rewizji."
            )
            warning.setWordWrap(True)
            layout.addWidget(warning)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.save_button = QPushButton("Zatwierdź import")
        self.save_button.setEnabled(False)
        self.confirm.toggled.connect(self.save_button.setEnabled)
        self.save_button.clicked.connect(self._save)
        cancel = QPushButton("Anuluj")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.save_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        if self.records:
            self.table.selectRow(0)

    def _details(self) -> None:
        row = self.table.currentRow()
        self.details.setPlainText(observation_text(self.records[row]) if row >= 0 else "")

    def _save(self) -> None:
        if not self.confirm.isChecked():
            return
        try:
            self.result_counts = self.database.fundamentals.import_package(self.package, confirmed=True,
                expected_preview_token=self.preview_token)
        except (ValueError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.warning(self, "Import przerwany", str(exc))
            return
        self.accept()


class FundamentalsDialog(QDialog):
    def __init__(self, database: Database, isin: str | None = None, as_of: str | None = None,
                 choose: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.database, self.choose, self.fixed_isin = database, choose, isin if choose else None
        self.selected_records: list[dict] = []
        self.records: list[dict] = []
        self.setWindowTitle("Historia danych fundamentalnych — porównanie okresów")
        self.resize(1200, 800)
        layout = QVBoxLayout(self)
        tools = QHBoxLayout()
        self.instrument_combo = QComboBox()
        tools.addWidget(self.instrument_combo, 1)
        import_button = QPushButton("Importuj JSON…")
        import_button.clicked.connect(self._import)
        tools.addWidget(import_button)
        layout.addLayout(tools)
        filters = QHBoxLayout()
        self.cutoff = QDateEdit(QDate.fromString(as_of or date.today().isoformat(), "yyyy-MM-dd"))
        self.cutoff.setCalendarPopup(True)
        self.cutoff.setDisplayFormat("dd.MM.yyyy")
        self.filter_available = QCheckBox("Tylko informacje dostępne na dzień:")
        self.filter_available.setChecked(choose)
        filters.addWidget(self.filter_available)
        filters.addWidget(self.cutoff)
        self.all_versions = QCheckBox("Pokaż także wcześniejsze wersje korekt")
        filters.addWidget(self.all_versions)
        layout.addLayout(filters)
        self.info = QLabel("To historia spółki, także sprzed zakupu. Zmiany okresowe nie oznaczają zmiany oceny inwestora. Wybierz wiersz, aby sprawdzić pochodzenie.")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.table = QTableWidget()
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.table, 1)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(210)
        layout.addWidget(self.details)
        self.table.itemSelectionChanged.connect(self._details)
        buttons = QHBoxLayout()
        if choose:
            self.latest_button = QPushButton("Wybierz najnowsze metryki")
            self.latest_button.clicked.connect(self.select_latest)
            buttons.addWidget(self.latest_button)
            context_button = QPushButton("Zaznacz cały widoczny kontekst")
            context_button.clicked.connect(self.table.selectAll)
            buttons.addWidget(context_button)
            apply_button = QPushButton("Użyj zaznaczonych danych w rewizji")
            apply_button.clicked.connect(self._use_selection)
            buttons.addWidget(apply_button)
            self.info.setText("Porównanie okresów spółki. Zaznaczone wiersze zostaną zachowane w rewizji; zaznacz także wcześniejsze okresy wykorzystane w ocenie (Ctrl/Shift lub cały kontekst). Najnowsze wybrane metryki wypełnią pola formularza.")
        close = QPushButton("Zamknij")
        close.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self._load_instruments(isin)
        self.instrument_combo.currentIndexChanged.connect(self.reload)
        self.filter_available.toggled.connect(self.reload)
        self.cutoff.dateChanged.connect(self.reload)
        self.all_versions.toggled.connect(self.reload)
        self.reload()

    def _load_instruments(self, selected: str | None = None) -> None:
        self.instrument_combo.blockSignals(True)
        self.instrument_combo.clear()
        instruments = {i["isin"]: f"{i['issuer_name']} / {i['share_class']} / {i['isin']}" for i in self.database.fundamentals.instruments()}
        for p in self.database.get_all_positions(include_closed=True):
            instruments.setdefault(p.isin, f"{p.ticker} / {p.isin}")
        if self.fixed_isin:
            instruments = {self.fixed_isin: instruments.get(self.fixed_isin, self.fixed_isin)}
        for isin, label in instruments.items():
            self.instrument_combo.addItem(label, isin)
        index = self.instrument_combo.findData(selected)
        self.instrument_combo.setCurrentIndex(max(index, 0))
        self.instrument_combo.blockSignals(False)

    def reload(self, *_args) -> None:
        isin = self.instrument_combo.currentData()
        self.records = self.database.fundamentals.history(isin,
            as_of=self.cutoff.date().toString("yyyy-MM-dd") if self.filter_available.isChecked() else None,
            all_versions=self.all_versions.isChecked()) if isin else []
        fill_table(self.table, self.records)
        self.details.setPlainText("Zaznacz dane, aby zobaczyć źródła, definicje i niepewność.")

    def _details(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.records):
            self.details.setPlainText(observation_text(self.records[row]))

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Pakiet danych fundamentalnych", "", "JSON (*.json)")
        if not path:
            return
        try:
            dialog = FundamentalImportDialog(self.database, path, self, expected_isin=self.fixed_isin)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.warning(self, "Nie można wczytać pakietu", str(exc))
            return
        self._load_instruments(self.fixed_isin or dialog.package["instruments"][0]["isin"])
        self.reload()

    def select_latest(self) -> None:
        self.table.clearSelection()
        groups = {}
        as_of = self.cutoff.date().toString("yyyy-MM-dd")
        for row, r in enumerate(self.records):
            o = r["observation"]
            if o["metric"] not in METRIC_LABELS or not available_on(o, as_of):
                continue
            groups.setdefault(o["metric"], []).append((row, r))
        ambiguous = []
        selection = self.table.selectionModel()
        from PySide6.QtCore import QItemSelectionModel
        for name, items in groups.items():
            signatures = {(r["observation"]["definition"], r["observation"]["scope"], r["observation"]["period"]["basis"], r["observation"]["currency"]) for _, r in items}
            if len(signatures) > 1:
                ambiguous.append(METRIC_LABELS[name])
                continue
            row, _ = max(items, key=lambda pair: (pair[1]["observation"]["valuation_date"] or pair[1]["observation"]["period"]["end"], pair[1]["id"]))
            selection.select(self.table.model().index(row, 0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        if ambiguous:
            self.details.setPlainText("Różne definicje/okresy wymagają ręcznego wyboru: " + ", ".join(ambiguous))

    def _use_selection(self) -> None:
        rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()})
        records = [self.records[row] for row in rows]
        if not records:
            QMessageBox.warning(self, "Wybierz dane", "Zaznacz metryki lub okresy do dołączenia do rewizji.")
            return
        if any(not available_on(r["observation"], self.cutoff.date().toString("yyyy-MM-dd")) for r in records):
            QMessageBox.warning(self, "Nieznana lub późniejsza publikacja", "Wybrane dane nie były potwierdzone jako dostępne w zadanym dniu.")
            return
        self.selected_records = records
        self.accept()


def show_review_evidence(review, parent: QWidget) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"Rewizja {review.review_date} — ocena i zachowany materiał")
    dialog.resize(850, 700)
    layout = QVBoxLayout(dialog)
    text = QTextEdit()
    text.setReadOnly(True)
    lines = [f"Data rzeczywistej rewizji: {review.review_date}",
             f"Automatyczna kategoria/instrukcja: {review.category} / {review.instruction}",
             f"Notatki / ocena inwestora:\n{review.notes or 'brak'}"]
    if review.fundamental_evidence_json:
        evidence = json.loads(review.fundamental_evidence_json)
        lines.append(f"Zapisano w dzienniku: {evidence['recorded_at']}")
        lines.append("Wartości użyte w formularzu:")
        for name, entry in evidence["metric_inputs"].items():
            lines.append(f"{METRIC_LABELS[name]}: {entry['value'] if entry['value'] is not None else 'brak'} ({'import' if entry['origin'] == 'imported' else 'ręcznie, pochodzenie nieustalone'})")
        lines.append("Zachowane kopie wybranych danych źródłowych:")
        lines.extend(observation_text(r) for r in evidence["observations"])
    else:
        lines.append("Zapis wcześniejszy: brak metadanych źródłowych. Nie odtwarzamy ich automatycznie.")
        lines.extend(f"{METRIC_LABELS[name]}: {review.metric_value(name) if review.metric_value(name) is not None else 'brak'}"
                     for name in METRIC_LABELS)
    text.setPlainText("\n\n".join(lines))
    layout.addWidget(text)
    close = QPushButton("Zamknij")
    close.clicked.connect(dialog.accept)
    layout.addWidget(close)
    dialog.exec()
