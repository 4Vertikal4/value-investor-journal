from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from src.config import (
    APP_NAME,
    APP_VERSION,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)

from src.database import (
    get_all_positions,
    insert_position,
)

from src.ui.dashboard_table import (
    DashboardTableModel,
    DashboardTableView,
)

from src.ui.position_dialog import (
    PositionDialog,
)


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

        self.setMinimumSize(
            WINDOW_MIN_WIDTH,
            WINDOW_MIN_HEIGHT,
        )

        self.table_model = DashboardTableModel()
        self.table_view = DashboardTableView()

        self._setup_ui()
        self.refresh_positions()

    # ========================================================
    # UI
    # ========================================================

    def _setup_ui(self) -> None:
        self._create_toolbar()
        self._create_statusbar()

        self.table_view.setModel(self.table_model)

        self.setCentralWidget(self.table_view)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")

        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        self.addToolBar(toolbar)

        # ====================================================
        # NOWA POZYCJA
        # ====================================================

        add_position_action = QAction(
            "Nowa pozycja",
            self,
        )

        add_position_action.triggered.connect(self._add_position)

        toolbar.addAction(add_position_action)

        # ====================================================
        # ODŚWIEŻ
        # ====================================================

        refresh_action = QAction(
            "Odśwież",
            self,
        )

        refresh_action.triggered.connect(self.refresh_positions)

        toolbar.addAction(refresh_action)

    def _create_statusbar(self) -> None:
        statusbar = QStatusBar()

        statusbar.showMessage("Gotowy")

        self.setStatusBar(statusbar)

    # ========================================================
    # DATA
    # ========================================================

    def refresh_positions(self) -> None:
        try:
            positions = get_all_positions()

            self.table_model.set_positions(positions)

            self.statusBar().showMessage(f"Załadowano {len(positions)} pozycji")

        except Exception as error:
            QMessageBox.critical(
                self,
                "Błąd bazy danych",
                str(error),
            )

    def _add_position(self) -> None:
        """
        Otwiera dialog dodawania pozycji.
        """

        dialog = PositionDialog(self)

        if dialog.exec():
            try:
                position = dialog.get_position()

                insert_position(position)

                self.refresh_positions()

                self.statusBar().showMessage(f"Dodano pozycję: {position.ticker}")

            except Exception as error:
                QMessageBox.critical(
                    self,
                    "Błąd zapisu",
                    str(error),
                )
