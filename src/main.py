from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox

from src.config import APP_NAME, DATA_DIR, IMPORTS_DIR
from src.database import Database
from src.notification_service import NotificationService
from src.ui.main_window import MainWindow
from src.ui.styles import apply_breeze_dark


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    ensure_directories()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_breeze_dark(app)

    database = Database()
    try:
        database.init()
    except Exception as exc:
        QMessageBox.critical(
            None, "Błąd startu", f"Nie udało się przygotować bazy danych:\n{exc}"
        )
        return 1

    window = MainWindow(database)
    window.show()
    notification_service = NotificationService(database, window, app)
    notification_service.check_due_reviews()
    app.setProperty("notification_service", notification_service)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
