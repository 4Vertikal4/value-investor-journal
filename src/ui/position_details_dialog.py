from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from src.database import (
    delete_position,
    update_position,
    insert_review,
    get_reviews_for_position,
)

from src.ui.review_dialog import ReviewDialog
from src.models import Position
from src.ui.position_dialog import PositionDialog


class PositionDetailsDialog(QDialog):
    def __init__(
        self,
        position: Position,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.position = position

        self.position_updated = False

        self.position_deleted = False

        self.setWindowTitle(f"{position.ticker} - Szczegóły pozycji")

        self.setMinimumWidth(700)

        self._build_ui()

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)

        form = QFormLayout()

        form.addRow(
            "Ticker",
            QLabel(self.position.ticker),
        )

        form.addRow(
            "Nazwa",
            QLabel(self.position.name),
        )

        form.addRow(
            "Sektor",
            QLabel(self.position.sector or "-"),
        )

        form.addRow(
            "Ilość",
            QLabel(str(self.position.quantity)),
        )

        form.addRow(
            "Cena zakupu",
            QLabel(f"{self.position.buy_price:.2f}"),
        )

        form.addRow(
            "Cena aktualna",
            QLabel(
                "-"
                if self.position.current_price is None
                else f"{self.position.current_price:.2f}"
            ),
        )

        form.addRow(
            "Wartość inwestycji",
            QLabel(f"{self.position.invested_value:.2f}"),
        )

        form.addRow(
            "Wartość rynkowa",
            QLabel(f"{self.position.market_value:.2f}"),
        )

        form.addRow(
            "Zwrot %",
            QLabel(f"{self.position.return_pct:.2f}%"),
        )

        form.addRow(
            "Data zakupu",
            QLabel(self.position.buy_date),
        )

        form.addRow(
            "Data rewizji",
            QLabel(self.position.review_date),
        )

        form.addRow(
            "Status",
            QLabel(self.position.status.value),
        )

        layout.addLayout(form)

        thesis = QPlainTextEdit()

        thesis.setReadOnly(True)

        thesis.setPlainText(self.position.thesis or "")

        thesis.setMinimumHeight(150)

        layout.addWidget(thesis)

        self.reviews_box = QPlainTextEdit()

        self.reviews_box.setReadOnly(True)

        self.reviews_box.setMinimumHeight(200)

        self._refresh_reviews()

        layout.addWidget(QLabel("Historia rewizji"))

        layout.addWidget(self.reviews_box)

        buttons = QDialogButtonBox()

        self.edit_button = buttons.addButton(
            "Edytuj",
            QDialogButtonBox.ActionRole,
        )

        self.review_button = buttons.addButton(
            "Dodaj rewizję",
            QDialogButtonBox.ActionRole,
        )

        self.delete_button = buttons.addButton(
            "Usuń",
            QDialogButtonBox.ActionRole,
        )

        buttons.addButton(
            QDialogButtonBox.Close,
        )

        self.edit_button.clicked.connect(self._edit_position)

        self.delete_button.clicked.connect(self._delete_position)

        self.review_button.clicked.connect(self._add_review)

        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout.addWidget(buttons)

    def _refresh_reviews(self) -> None:

        reviews = get_reviews_for_position(self.position.id)

        if not reviews:
            self.reviews_box.setPlainText("Brak rewizji.")
            return

        lines = []

        for review in reviews:

            lines.append(review.review_date)

            lines.append(review.category.value)

            lines.append(review.instruction.value)

            if review.notes:
                lines.append(review.notes)

            lines.append("-" * 40)

        self.reviews_box.setPlainText("\n".join(lines))

    def _edit_position(self) -> None:

        dialog = PositionDialog(
            position=self.position,
            parent=self,
        )

        if dialog.exec():

            updated_position = dialog.get_position()

            update_position(updated_position)

            self.position_updated = True

            self.accept()

    def _delete_position(self) -> None:

        answer = QMessageBox.question(
            self,
            "Usuń pozycję",
            (f"Czy na pewno usunąć " f"pozycję {self.position.ticker}?"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        delete_position(self.position.id)

        self.position_deleted = True

        self.accept()

    def _add_review(self) -> None:

        dialog = ReviewDialog(
            position=self.position,
            parent=self,
        )

        if not dialog.exec():
            return

        review = dialog.get_review()

        insert_review(review)

        self._refresh_reviews()

        QMessageBox.information(
            self,
            "Rewizja",
            "Rewizja została zapisana.",
        )
