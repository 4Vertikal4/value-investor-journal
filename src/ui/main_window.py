from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    APP_NAME,
    CATEGORY_STYLES,
    METRIC_FIELDS,
    METRIC_LABELS,
    METRIC_UNITS,
    STATUS_CLOSED,
    UI,
)
from src.database import Database
from src.exporter import (
    backup_database,
    export_positions_csv,
    export_reviews_csv,
    export_xlsx,
)
from src.importer_lightyear import import_lightyear_csv
from src.metrics_engine import compare_metric, describe_metric_change, get_trend_color
from src.models import Position, Review
from src.rule_engine import calculate_return, categorize_with_thresholds, format_return
from src.ui.asset_allocation_widget import AssetAllocationWidget
from src.ui.dashboard_table import DashboardTable
from src.ui.position_dialog import PositionDialog
from src.ui.review_dialog import ReviewDialog


class MainWindow(QMainWindow):
    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.database = database
        self.positions_list: list[Position] = []
        self.show_closed = False
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 760)
        self.build_actions()
        self.build_ui()
        self.build_menu()
        self.build_toolbar()
        self.connect_signals()
        self.refresh_data()

    def build_actions(self) -> None:
        self.add_action = QAction(UI["add position"], self)
        self.add_action.setShortcut(QKeySequence("Ctrl+N"))
        self.review_action = QAction(UI["add review"], self)
        self.review_action.setShortcut(QKeySequence("Ctrl+R"))
        self.import_action = QAction(UI["import csv"], self)
        self.import_action.setShortcut(QKeySequence("Ctrl+I"))
        self.export_xlsx_action = QAction(UI["Eksport XLSX"], self)
        self.export_xlsx_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_csv_action = QAction(UI["Eksport CSV"], self)
        self.backup_action = QAction(UI["Eksportuj backup bazy"], self)
        self.allocation_action = QAction(UI["allocation"], self)
        self.allocation_action.setShortcut(QKeySequence("Ctrl+A"))
        self.refresh_action = QAction(UI["refresh"], self)
        self.refresh_action.setShortcut(QKeySequence("F5"))
        self.show_closed_action = QAction(UI["Pokaż zamknięte"], self)
        self.show_closed_action.setCheckable(True)
        self.refresh_metrics_action = QAction(UI["Odśwież metryki"], self)
        self.notifications_action = QAction(UI["Powiadomienia"], self)
        self.notifications_action.setCheckable(True)
        self.exit_action = QAction("Wyjdz", self)
        self.about_action = QAction(UI["about"], self)

    def build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = DashboardTable()
        splitter.addWidget(self.table)
        splitter.addWidget(self.build_detail_pane())
        splitter.setSizes([760, 520])
        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Gotowe")

    def build_detail_pane(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        header_row = QHBoxLayout()
        self.detail_ticker_label = QLabel("Wybierz pozycję")
        self.detail_ticker_label.setStyleSheet(
            "font-size: 18pt; font-weight: bold; color: #FFFFFF;"
        )
        self.detail_sector_badge = QLabel("")
        self.detail_sector_badge.setStyleSheet(
            "background-color: #3A3A3A; border-radius: 8px; padding: 4px 10px; color: #CCCCCC;"
        )
        header_row.addWidget(self.detail_ticker_label)
        header_row.addStretch()
        header_row.addWidget(self.detail_sector_badge)
        layout.addLayout(header_row)

        numbers_frame = QFrame()
        numbers_frame.setObjectName("DetailCard")
        numbers_layout = QFormLayout(numbers_frame)
        self.detail_labels = {}
        for key, label in [
            ("key_price", "Cena zakupu"),
            ("current_price", "Aktualna"),
            ("return", "Zwrot"),
            ("category", "Kategoria"),
            ("instruction", "Instrukcja"),
            ("next_review", "Następna rewizja"),
        ]:
            value_label = QLabel("—")
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            if key in ("category", "instruction"):
                value_label.setStyleSheet("font-weight: bold;")
            self.detail_labels[key] = value_label
            numbers_layout.addRow(label, value_label)
        layout.addWidget(numbers_frame)

        layout.addSpacing(15)
        self.thesis_text = QTextEdit()
        self.thesis_text.setReadOnly(True)
        self.thesis_text.setMaximumHeight(100)
        layout.addWidget(self.thesis_text)

        metrics_group = QGroupBox("Metryki fundamentalne")
        self.metrics_grid = QGridLayout(metrics_group)
        layout.addWidget(metrics_group)

        self.review_history_group = QGroupBox("Historia rewizji")
        self.review_history_group.setCheckable(True)
        self.review_history_group.setChecked(True)
        history_layout = QVBoxLayout(self.review_history_group)
        self.review_history_table = QTableWidget(0, 3)
        self.review_history_table.setHorizontalHeaderLabels(
            ("Data", "Cena", "Kategoria")
        )
        self.review_history_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.review_history_table.horizontalHeader().setVisible(False)
        history_layout.addWidget(self.review_history_table)
        history_layout.addStretch()
        layout.addWidget(self.review_history_group)
        self.review_history_group.toggled.connect(self.review_history_table.setVisible)

        return panel

    def build_menu(self) -> None:
        file_menu = self.menuBar().addMenu(UI["file"])
        file_menu.addAction(self.import_action)
        file_menu.addSeparator()
        file_menu.addAction(self.backup_action)
        file_menu.addAction(self.export_xlsx_action)
        file_menu.addAction(self.export_csv_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        view_menu = self.menuBar().addMenu(UI["view"])
        view_menu.addAction(self.refresh_action)
        view_menu.addAction(self.show_closed_action)
        view_menu.addAction(self.refresh_metrics_action)
        view_menu.addAction(self.notifications_action)

        help_menu = self.menuBar().addMenu(UI["help"])
        help_menu.addAction(self.about_action)

    def build_toolbar(self) -> None:
        toolbar = QToolBar("Główne akcje")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        for action in (
            self.add_action,
            self.review_action,
            self.import_action,
            self.export_xlsx_action,
            self.allocation_action,
            self.refresh_action,
        ):
            toolbar.addAction(action)

    def connect_signals(self) -> None:
        self.add_action.triggered.connect(self.add_position)
        self.review_action.triggered.connect(self.add_review_for_selected)
        self.import_action.triggered.connect(self.import_csv)
        self.export_xlsx_action.triggered.connect(self.export_xlsx_file)
        self.export_csv_action.triggered.connect(self.export_csv_file)
        self.backup_action.triggered.connect(self.backup_database)
        self.allocation_action.triggered.connect(self.open_asset_allocation)
        self.refresh_action.triggered.connect(self.refresh_data)
        self.show_closed_action.toggled.connect(self.toggle_closed)
        self.refresh_metrics_action.triggered.connect(self.update_metrics)
        self.notifications_action.toggled.connect(self.show_notifications)
        self.about_action.triggered.connect(self.show_about)
        self.table.positionDoubleClicked.connect(self.select_position)
        self.table.itemChanged.connect(self.update_details)
        self.table.customContextMenuRequested.connect(self.open_context_menu)

    def refresh_data(self) -> None:
        try:
            self.positions = self.database.get_all_positions(
                include_closed=self.show_closed
            )
        except Exception as exc:
            QMessageBox.critical(self, "Błąd bazy", str(exc))
            return
        self.update_details(self.positions[0]) if self.positions else None
        selected = self.table.selected_position
        if selected and selected in self.positions:
            self.update_details(selected)
        total = self.database.get_portfolio_value(include_closed=self.show_closed)
        self.statusBar().showMessage(
            f"Liczba pozycji: {len(self.positions)} | Suma portfela: {total:.2f} | Ostatnia aktualizacja: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def update_details(self, position: Position | None = None) -> None:
        if position is None:
            self.detail_ticker_label.setText("Wybierz pozycję")
            self.detail_sector_badge.setText("")
            for label in self.detail_labels:
                self.detail_labels[label].setText("—")
            self.thesis_text.clear()
            self.clear_metrics_grid()
            self.review_history_table.setRowCount(0)
            return
        try:
            position = self.database.get_position_by_id(position.id or 0) or position
            reviews = self.database.get_reviews_for_position(position.id or 0)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd bazy", str(exc))
            return
        current = position.display_price()
        ret = calculate_return(position.buy_price, current)
        category, instruction = categorize_with_thresholds(
            ret,
            position.threshold_gain,
            position.threshold_profit,
            position.threshold_loss,
        )
        style = CATEGORY_STYLES.get(category, CATEGORY_STYLES["NEUTRAL"])
        self.detail_ticker_label.setText(f"{position.ticker} {position.name}")
        self.detail_sector_badge.setText(position.sector or "Brak sektora")
        self.detail_sector_badge.setStyleSheet(
            f"background-color: {style['color']}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;"
        )
        self.detail_labels["key_price"].setText(
            f"{position.buy_price:.2f} {position.currency}"
        )
        self.detail_labels["current_price"].setText(
            f"{current:.2f} {position.currency}"
        )
        self.detail_labels["return"].setText(f"{ret:.2f}%")
        self.detail_labels["return"].setStyleSheet(
            f"color: {style['color']}; font-weight: bold;"
        )
        self.detail_labels["category"].setText(category)
        self.detail_labels["category"].setStyleSheet(f"color: {style['color']};")
        self.detail_labels["instruction"].setText(instruction)
        self.detail_labels["instruction"].setStyleSheet(f"color: {style['color']};")
        self.detail_labels["next_review"].setText(
            position.next_review_date.strftime("%Y-%m-%d")
            if position.next_review_date
            else "Brak"
        )
        self.thesis_text.setText(
            position.thesis or "Brak zapisanej tezy inwestycyjnej."
        )
        self.update_metrics_grid(position)
        self.update_reviews_history(reviews)
        self.table.select_position(position)
        self.review_history_group.setEnabled(True)
        self.detail_labels["instruction"].setText(instruction)
        self.detail_labels["instruction"].setStyleSheet(f"color: {style['color']};")
        self.detail_labels["next_review"].setText(
            position.next_review_date.strftime("%Y-%m-%d")
            if position.next_review_date
            else "Brak"
        )
        self.thesis_text.setText(
            position.thesis or "Brak zapisanej tezy inwestycyjnej."
        )
        self.update_metrics_grid(position)
        self.update_reviews_history(reviews)
        self.table.select_position(position)
        self.review_history_group.setEnabled(True)

    def get_review_date_label(self, review_date: str) -> None:
        label = QLabel()
        label.setText("Nieznana data")
        try:
            parsed = date.fromisoformat(review_date)
        except ValueError:
            return
        if parsed.date() == date.today():
            label.setText("Dzisiaj")
            label.setStyleSheet("color: #FFA500; font-weight: bold;")
        elif parsed.date() == date.today() - timedelta(days=1):
            label.setText("Wczoraj")
            label.setStyleSheet("color: #FFA500; font-weight: bold;")
        else:
            label.setText(review_date)
        return label

    def update_metrics_grid(self, position: Position) -> None:
        last = reviews[-1] if reviews else None
        previous = reviews[-2] if len(reviews) > 1 else None
        row = 0
        for col, title in enumerate(("Wskaźnik", "Wartość", "Poprzednio")):
            label = QLabel(title)
            label.setStyleSheet("font-weight: bold; color: #FFFFFF;")
            self.metrics_grid.addWidget(label, row, col)
        row += 1
        for row, metric_name in enumerate(METRIC_FIELDS, start=1):
            current_value = (
                position.metrics.get(metric_name) if position.metrics else None
            )
            previous_value = (
                previous.metrics.get(metric_name)
                if previous and previous.metrics
                else None
            )
            change = compare_metric(metric_name, current_value, previous_value)
            color, emoji = get_trend_color(change)
            label = QLabel(METRIC_LABELS.get(metric_name, metric_name))
            unit = METRIC_UNITS.get(metric_name, "")
            current_text = (
                f"{current_value:.2f}{unit}" if current_value is not None else "—"
            )
            previous_text = (
                f"{previous_value:.2f}{unit}" if previous_value is not None else "—"
            )
            self.metrics_grid.addWidget(label, row, 0)
            for col, value in enumerate(
                (current_text, previous_text, f"{emoji} {change}")
            ):
                if col == 1:
                    label = QLabel(value)
                    label.setStyleSheet(f"color: {color}; font-weight: bold;")
                elif col == 2:
                    label = QLabel(value)
                    label.setStyleSheet(f"color: {color};")
                else:
                    label = QLabel(value)
                self.metrics_grid.addWidget(label, row, col + 1)

    def update_reviews_history(self, reviews: list[Review], currency: str) -> None:
        self.review_history_table.setRowCount(len(reviews))
        for row, review in enumerate(reviews):
            values = [
                review.review_date,
                f"{review.price_than:.4f} {currency}",
                format_return(review.return_pct),
                review.category,
            ]
            style = CATEGORY_STYLES.get(review.category, CATEGORY_STYLES["NEUTRAL"])
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (1, 2):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if col in (1, 3):
                    item.setForeground(QColor(style["fg"]))
                font = QFont()
                font.setBold(True)
                item.setFont(font)
                self.review_history_table.setItem(row, col, item)
        self.review_history_table.resizeColumnsToContents()

    def clear_layout(self, layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_position(self) -> None:
        dialog = PositionDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        position = dialog.get_position()
        try:
            self.database.insert_position(position)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd dodawania", str(exc))
            return
        self.refresh_data()

    def edit_position(self, position: Position) -> None:
        current = self.database.get_position_by_id(position.id or 0)
        if current is None:
            QMessageBox.warning(self, "Pozycja", "Nie znaleziono pozycji w bazie.")
            return
        dialog = PositionDialog(current, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.get_position()
        try:
            self.database.update_position(updated)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd edycji", str(exc))

    def add_review_for_selected(self) -> None:
        position = self.table.selected_position()
        self.add_review(position)

    def add_review(self, position: Position | None = None) -> None:
        selected_id = position.id if position is not None else None
        dialog = ReviewDialog(self.database, selected_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()

    def open_context_menu(self, position: Position, global_pos: Any) -> None:
        menu = QMenu(self)
        review_action = menu.addAction("Dodaj rewizję")
        edit_action = menu.addAction("Edytuj")
        close_text = (
            "Otwórz ponownie" if position.status == STATUS_CLOSED else "Zamknij pozycję"
        )
        close_action = menu.addAction(close_text)
        menu.addSeparator()
        delete_action = menu.addAction("Usuń")
        selected = menu.exec(global_pos)
        if selected == review_action:
            self.add_review(position)
        elif selected == edit_action:
            self.edit_position(position)
        elif selected == close_action:
            self.toggle_position_status(position)
        elif selected == delete_action:
            self.delete_position(position)

    def toggle_position_status(self, position: Position) -> None:
        try:
            if position.status == STATUS_CLOSED:
                self.database.reopen_position(position.id or 0)
            else:
                self.database.close_position(position.id or 0)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd statusu", str(exc))
            return
        self.refresh_data()

    def delete_position(self, position: Position) -> None:
        answer = QMessageBox.question(
            self,
            "Usuń pozycję",
            f"Usuń pozycję {position.ticker} wraz z historią rewizji?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_position(position.id or 0)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd usuwania", str(exc))
            return
        self.refresh_data()

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importuj CSV lightyear",
            str(Path.home()),
            "CSV (*.csv);;Wszystkie pliki (*)",
        )
        if not path:
            return
        try:
            result = import_lightyear_csv(Path(path), self.database)
        except Exception as exc:
            QMessageBox.critical(self, "Import lightyear", str(exc))
            return
        QMessageBox.information(
            self,
            "Import lightyear",
            f"Gotowo: {result.inserted} zaaktualizowano: {result.updated} pominięto: {result.skipped} błędów: {len(result.errors)}",
        )
        self.refresh_data()

    def export_xlsx_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport XLSX",
            str(Path.home() / "dziennik_inwestora.xlsx"),
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            export_xlsx(Path(path), self.database)
        except Exception as exc:
            QMessageBox.critical(self, "Eksport XLSX", str(exc))
            return
        QMessageBox.information(self, "Eksport XLSX", "Eksport zakończony.")

    def export_csv_file(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Katalog eksportu CSV", str(Path.home())
        )
        if not directory:
            return
        try:
            export_positions_csv(Path(directory) / "positions.csv", self.database)
            export_reviews_csv(Path(directory) / "reviews.csv", self.database)
        except Exception as exc:
            QMessageBox.critical(self, "Eksport CSV", str(exc))
            return
        QMessageBox.information(
            self, "Eksport CSV", "Wyeksportowano positions.csv i reviews.csv"
        )

    def delete_position(self, position: Position) -> None:
        answer = QMessageBox.question(
            self,
            "Usuń pozycję",
            f"Usuń pozycję {position.ticker} wraz z historią rewizji?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.delete_position(position.id or 0)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd usuwania", str(exc))
            return
        self.refresh_data()

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importuj CSV lightyear",
            str(Path.home()),
            "CSV (*.csv);;Wszystkie pliki (*)",
        )
        if not path:
            return
        try:
            result = import_lightyear_csv(Path(path), self.database)
        except Exception as exc:
            QMessageBox.critical(self, "Import lightyear", str(exc))
            return
        QMessageBox.information(
            self,
            "Import lightyear",
            f"Gotowo: {result.inserted} zaaktualizowano: {result.updated} pominięto: {result.skipped} błędów: {len(result.errors)}",
        )
        self.refresh_data()

    def export_xlsx_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport XLSX",
            str(Path.home() / "dziennik_inwestora.xlsx"),
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            export_xlsx(Path(path), self.database)
        except Exception as exc:
            QMessageBox.critical(self, "Eksport XLSX", str(exc))
            return
        QMessageBox.information(self, "Eksport XLSX", "Eksport zakończony.")

    def export_csv_file(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Katalog eksportu CSV", str(Path.home())
        )
        if not directory:
            return
        try:
            export_positions_csv(Path(directory) / "positions.csv", self.database)
            export_reviews_csv(Path(directory) / "reviews.csv", self.database)
        except Exception as exc:
            QMessageBox.critical(self, "Eksport CSV", str(exc))
            return
        QMessageBox.information(
            self, "Eksport CSV", "Wyeksportowano positions.csv i reviews.csv"
        )

    def export_backup_file(self) -> None:
        default = Path.home() / f"dziennik_backup_{date.today().isoformat()}.db"
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup bazy", str(default), "SQLite DB (*.db);;Wszystkie pliki (*)"
        )
        if not path:
            return
        try:
            backup_database(Path(path), self.database)
        except Exception as exc:
            QMessageBox.critical(self, "Backup bazy", str(exc))
            return
        QMessageBox.information(self, "Backup bazy", "Backup zapisany.")

    def open_asset_allocation(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Alokacja aktywów")
        dialog.resize(640, 640)
        layout = QVBoxLayout(dialog)
        layout.addWidget(AssetAllocationWidget(self.database, dialog))
        dialog.exec()

    def toggle_closed(self, checked: bool) -> None:
        self.show_closed = checked
        self.refresh_data()

    def offline_metrics_message(self) -> None:
        QMessageBox.information(
            self,
            "Tryb offline",
            "Automatyczne pobieranie metryk jest wyłączone. W tej wersji dane wpisujesz ręcznie albo importujesz z CSV.",
        )

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"O aplikacji {APP_NAME}",
            f"{APP_NAME}\n\nInwestycyjny dziennik wartości inwestora oparty o SQLite, PySide6 i jasne reguły inwestycyjne.",
        )
