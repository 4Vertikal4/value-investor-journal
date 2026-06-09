from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QTextEdit,
    QVBoxLayout,
)

from src.models import (
    Position,
    Review,
    ReviewCategory,
    ReviewInstruction,
)


class ReviewDialog(QDialog):
    def __init__(
        self,
        position: Position,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.position = position

        self.setWindowTitle(f"Nowa rewizja - {position.ticker}")

        self.setMinimumWidth(500)

        self._build_ui()

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.review_date_edit = QDateEdit()

        self.review_date_edit.setCalendarPopup(True)

        self.review_date_edit.setDate(date.today())

        self.category_combo = QComboBox()

        for category in ReviewCategory:
            self.category_combo.addItem(category.value)

        self.instruction_combo = QComboBox()

        for instruction in ReviewInstruction:
            self.instruction_combo.addItem(instruction.value)

        self.notes_edit = QTextEdit()

        self.notes_edit.setPlaceholderText("Wnioski z rewizji...")

        self.notes_edit.setMinimumHeight(150)

        form.addRow(
            "Data rewizji",
            self.review_date_edit,
        )

        form.addRow(
            "Kategoria",
            self.category_combo,
        )

        form.addRow(
            "Instrukcja",
            self.instruction_combo,
        )

        form.addRow(
            "Notatki",
            self.notes_edit,
        )

        layout.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        self.buttons.accepted.connect(self.accept)

        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

    def get_review(self) -> Review:

        current_price = (
            self.position.current_price
            if self.position.current_price is not None
            else self.position.buy_price
        )

        return Review(
            id=None,
            position_id=self.position.id,
            review_date=self.review_date_edit.date().toString("yyyy-MM-dd"),
            price_then=current_price,
            return_pct=self.position.return_pct,
            category=ReviewCategory(self.category_combo.currentText()),
            instruction=ReviewInstruction(self.instruction_combo.currentText()),
            notes=self.notes_edit.toPlainText().strip() or None,
        )
