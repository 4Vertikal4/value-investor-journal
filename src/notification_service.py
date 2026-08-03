from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from src.database import Database


class NotificationService(QObject):
    def __init__(
        self, database: Database, main_window: object, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.database = database
        self.main_window = main_window
        self.enabled = True
        self.muted_until: datetime | None = None
        app = QApplication.instance()
        style = app.style() if app is not None else None
        icon = (
            style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            if style is not None
            else None
        )
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Dziennik Inwestora Value")
        self._build_menu()
        self.tray.activated.connect(self._activated)
        self.tray.show()

        self.timer = QTimer(self)
        self.timer.setInterval(60 * 60 * 1000)
        self.timer.timeout.connect(self.check_due_reviews)
        self.timer.start()

        notifications_action = getattr(main_window, "notifications_action", None)
        if notifications_action is not None:
            notifications_action.toggled.connect(self.set_enabled)

    def _build_menu(self) -> None:
        menu = QMenu()
        open_action = QAction("Otwórz", menu)
        review_action = QAction("Dodaj szybką rewizję", menu)
        mute_action = QAction("Wycisz na 1h", menu)
        quit_action = QAction("Wyjdź", menu)
        open_action.triggered.connect(self.open_main_window)
        review_action.triggered.connect(self.add_quick_review)
        mute_action.triggered.connect(self.mute_for_one_hour)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(open_action)
        menu.addAction(review_action)
        menu.addAction(mute_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.open_main_window()

    def open_main_window(self) -> None:
        window = self.main_window
        if hasattr(window, "showNormal"):
            window.showNormal()
        if hasattr(window, "raise_"):
            window.raise_()
        if hasattr(window, "activateWindow"):
            window.activateWindow()

    def add_quick_review(self) -> None:
        self.open_main_window()
        callback: Callable[[], None] | None = getattr(
            self.main_window, "add_review_for_selected", None
        )
        if callback is not None:
            callback()

    def mute_for_one_hour(self) -> None:
        self.muted_until = datetime.now() + timedelta(hours=1)
        self.show_notification(
            "Powiadomienia wyciszone", "Przypomnienia o rewizjach wrócą za godzinę."
        )

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if enabled:
            self.show_notification(
                "Powiadomienia aktywne", "Przypomnienia o rewizjach są włączone."
            )
        else:
            self.show_notification(
                "Powiadomienia wyłączone", "Przypomnienia o rewizjach są wyłączone."
            )

    def check_due_reviews(self) -> None:
        if not self.enabled:
            return
        if self.muted_until is not None and datetime.now() < self.muted_until:
            return
        due = self.database.due_positions()
        if not due:
            return
        tickers = ", ".join(position.ticker for position in due[:5])
        suffix = "" if len(due) <= 5 else f" i {len(due) - 5} więcej"
        self.show_notification(
            "Czas na rewizję pozycji",
            f"Pozycje wymagające przeglądu: {tickers}{suffix}.",
            QSystemTrayIcon.MessageIcon.Warning,
        )

    def show_notification(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ) -> None:
        if self.tray.isVisible():
            self.tray.showMessage(title, message, icon, 8000)

    def quit_app(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()
