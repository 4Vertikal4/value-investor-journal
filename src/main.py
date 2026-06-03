from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.config import (
    APP_NAME,
    APP_VERSION,
    ORG_NAME,
    ensure_directories,
)
from src.database import init_db
from src.ui.main_window import MainWindow
from src.ui.styles import apply_theme


def main() -> int:
    """
    Główny entrypoint aplikacji.
    """

    # ========================================================
    # INIT
    # ========================================================

    ensure_directories()

    init_db()

    # ========================================================
    # QT APPLICATION
    # ========================================================

    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)

    # KDE / Plasma integration
    app.setDesktopFileName("value-investor-journal")

    # ========================================================
    # THEME
    # ========================================================

    apply_theme(app)

    # ========================================================
    # MAIN WINDOW
    # ========================================================

    window = MainWindow()

    window.show()

    # ========================================================
    # EVENT LOOP
    # ========================================================

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
