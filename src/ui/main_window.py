from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem, QDialog, QFileDialog,
    QMessageBox, QMenu, QLineEdit, QComboBox, QFormLayout, QFrame, QListWidget
)

APP_NAME = 'MyApp'  # Zastąp rzeczywistą nazwą aplikacji
VERSION = '1.0'     # Zastąp rzeczywistą wersją aplikacji

class MainWindow(QMainWindow):
    def __init__(self, database: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.database = database
        self.positions: list[Position] = []  # Lista pozycji (Position) pobrana z bazy danych
        self._data_loaded = False
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 760)
        self.setup_ui()
        self.statusBar().showMessage('Gotowe')

    def setup_ui(self) -> None:
        # Ustawienie głównego widgetu i menu
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.addWidget(self.build_main_panel())
        self.setCentralWidget(central)
        self.create_menus()

    def build_main_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        # Nagłówek z informacją
        header_row = QHBoxLayout()
        self.header_label = QLabel('Wybierz pozycję')
        self.header_label.setStyleSheet('font-size: 18pt; font-weight: bold; color: #FFFFFF;')
        header_row.addWidget(self.header_label)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Grupa historii (przykładowa zawartość)
        self.history_group = QGroupBox('Historia')
        self.history_group.setCheckable(True)
        self.history_group.setChecked(True)
        history_layout = QVBoxLayout()
        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels([
            'Kolumna1', 'Kolumna2', 'Kolumna3', 'Kolumna4'
        ])  # Ustaw odpowiednie nagłówki
        history_layout.addWidget(self.history_table)
        self.history_group.setLayout(history_layout)
        layout.addWidget(self.history_group)

        return panel

    def create_menus(self) -> None:
        # Tworzenie paska menu
        file_menu = self.menuBar().addMenu('&File')
        # Przykładowe akcje dla menu Plik (dodaj właściwe akcje/metody)
        # file_menu.addAction(self.action_new_db)
        # file_menu.addAction(self.action_backup_db)
        # file_menu.addAction(self.action_restore_db)
        # file_menu.addAction(self.action_exit)

        view_menu = self.menuBar().addMenu('&View')
        # Przykładowe akcje dla menu Widok
        # view_menu.addAction(self.action_show_history)

    def add_review_for_selected(self) -> None:
        # Dodaj rewizję dla aktualnie zaznaczonej pozycji w tabeli
        selected_row = self.history_table.currentRow()
        if selected_row < 0 or selected_row >= len(self.positions):
            QMessageBox.warning(self, 'Pozycja', 'Nie znaleziono pozycji')
            return
        position = self.positions[selected_row]
        self.add_review(position)

    def add_review(self, position: Position | None = None) -> None:
        selected_id = position.id if position is not None else None
        dialog = ReviewDialog(self.database, selected_id, self)
        if dialog.exec() == QDialog.Accepted:
            # Po dodaniu rewizji odśwież listę rewizji
            self.update_reviews(position)

    def update_reviews(self, position: Position) -> None:
        # Aktualizuj tabelę rewizji dla danej pozycji
        # Przykładowo pobieranie rewizji z bazy danych
        reviews, currency = self.database.get_reviews_for_position(position.id)
        self.history_table.setRowCount(len(reviews))
        for row, review in enumerate(reviews):
            # Przygotowanie wartości do wyświetlenia (dostosuj wg potrzeb)
            values = [
                f"{review.value:.2f} {currency}",
                f"{review.return:.2f}",
                CATEGORY_STYLES.get(review.category, review.category),
                format_date(review.date)
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                self.history_table.setItem(row, col, item)

    def context_menu_requested(self, position: Position, global_pos: Any) -> None:
        # Kontekstowe menu dla tabeli (np. dodaj/usuń rewizję)
        menu = QMenu(self)
        add_action = menu.addAction("Dodaj rewizję")
        delete_action = menu.addAction("Usuń rewizję")
        action = menu.exec(global_pos)
        if action == add_action:
            self.add_review(position)
        elif action == delete_action:
            reply = QMessageBox.question(
                self, 'Usuń rewizję', 'Czy na pewno chcesz usunąć tę rewizję?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    self.database.delete_review(position.id or 0, position.selected_review_id)
                    self.update_reviews(position)
                except Exception as exc:
                    QMessageBox.critical(self, 'Błąd usuwania', str(exc))

    def export_reviews(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, 'Katalog eksportu', str(Path.cwd()))
        if not directory:
            return
        try:
            export_reviews_csv(Path(directory) / 'ws.csv', self.database)
            QMessageBox.information(self, 'Eksport CSV', 'Eksport zakończony.')
        except Exception as exc:
            QMessageBox.critical(self, 'Eksport CSV', str(exc))

    def backup_database(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Zapisz bazę', str(Path.cwd() / 'backup.db'))
        if not path:
            return
        try:
            backup_database(Path(path), self.database)
            QMessageBox.information(self, 'Backup', 'Kopia zapasowa wykonana.')
        except Exception as exc:
            QMessageBox.critical(self, 'Błąd', str(exc))

    def restore_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Wybierz plik', str(Path.cwd()), '*.db')
        if not path:
            return
        try:
            restore_database(Path(path), self.database)
            QMessageBox.information(self, 'Przywracanie', 'Przywracanie zakończone.')
        except Exception as exc:
            QMessageBox.critical(self, 'Błąd', str(exc))

    def show_about(self) -> None:
        QMessageBox.information(
            self, 'O aplikacji',
            f"{APP_NAME} v{VERSION}\nAplikacja do zarządzania..."
        )

if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    database = Database()  # Zainicjalizuj obiekt bazy danych
    window = MainWindow(database)
    window.show()
    sys.exit(app.exec())
