from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from src.config import DEFAULT_CURRENCY
from src.models import (
    Position,
    PositionStatus,
)


class PositionDialog(QDialog):
    """
    Dialog dodawania nowej pozycji.
    """

    def __init__(
        self,
        position: Position | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.position = position

        self.setWindowTitle("Nowa pozycja")
        self.setMinimumWidth(500)

        self._build_ui()

        if self.position is not None:
            self._load_position()

    def _load_position(self) -> None:

        self.ticker_edit.setText(self.position.ticker)

        self.name_edit.setText(self.position.name)

        self.sector_edit.setText(self.position.sector or "")

        self.thesis_edit.setPlainText(self.position.thesis or "")

        self.quantity_spin.setValue(self.position.quantity)

        self.buy_price_spin.setValue(self.position.buy_price)

        self.currency_combo.setCurrentText(self.position.currency)

        self.ticker_edit.setReadOnly(True)

        self.setWindowTitle(f"Edytuj pozycję - {self.position.ticker}")

        self.buy_date_edit.setDate(
            QDate.fromString(
                self.position.buy_date,
                "yyyy-MM-dd",
            )
        )

        self.review_date_edit.setDate(
            QDate.fromString(
                self.position.review_date,
                "yyyy-MM-dd",
            )
        )

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)

        form = QFormLayout()

        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(20)

        # ----------------------------------------------------
        # BASIC INFO
        # ----------------------------------------------------

        self.ticker_edit = QLineEdit()
        self.ticker_edit.setPlaceholderText("np. KRU")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("np. Kruk S.A.")

        self.sector_edit = QLineEdit()
        self.sector_edit.setPlaceholderText("np. Finanse")

        self.thesis_edit = QTextEdit()
        self.thesis_edit.setMaximumHeight(120)
        self.thesis_edit.setPlaceholderText("Dlaczego kupiłeś tę spółkę?")

        # ----------------------------------------------------
        # POSITION DATA
        # ----------------------------------------------------

        self.quantity_spin = QDoubleSpinBox()

        self.quantity_spin.setMinimum(0.0001)

        self.quantity_spin.setMaximum(1_000_000)

        self.quantity_spin.setDecimals(4)

        self.quantity_spin.setValue(1.0)

        self.buy_price_spin = QDoubleSpinBox()

        self.buy_price_spin.setMinimum(0.01)

        self.buy_price_spin.setMaximum(1_000_000)

        self.buy_price_spin.setDecimals(2)

        # ----------------------------------------------------
        # CURRENCY
        # ----------------------------------------------------

        self.currency_combo = QComboBox()

        self.currency_combo.addItems(
            [
                "PLN",
                "EUR",
                "USD",
                "GBP",
            ]
        )

        self.currency_combo.setCurrentText(DEFAULT_CURRENCY)

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        self.buy_date_edit = QDateEdit()

        self.buy_date_edit.setCalendarPopup(True)

        self.buy_date_edit.setDate(date.today())

        self.review_date_edit = QDateEdit()

        self.review_date_edit.setCalendarPopup(True)

        self.review_date_edit.setDate(date.today())

        # ----------------------------------------------------
        # FORM
        # ----------------------------------------------------

        form.addRow(
            "Ticker *",
            self.ticker_edit,
        )

        form.addRow(
            "Nazwa *",
            self.name_edit,
        )

        form.addRow(
            "Sektor",
            self.sector_edit,
        )

        form.addRow(
            "Teza inwestycyjna",
            self.thesis_edit,
        )

        form.addRow(
            "Ilość *",
            self.quantity_spin,
        )

        form.addRow(
            "Cena zakupu *",
            self.buy_price_spin,
        )

        form.addRow(
            "Waluta",
            self.currency_combo,
        )

        form.addRow(
            "Data zakupu",
            self.buy_date_edit,
        )

        form.addRow(
            "Data rewizji",
            self.review_date_edit,
        )

        layout.addLayout(form)

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        self.buttons.accepted.connect(self._validate)

        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)

    # ========================================================
    # VALIDATION
    # ========================================================

    def _validate(self) -> None:

        if not self.ticker_edit.text().strip():
            QMessageBox.warning(
                self,
                "Błąd",
                "Ticker jest wymagany.",
            )
            return

        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self,
                "Błąd",
                "Nazwa jest wymagana.",
            )
            return

        if self.quantity_spin.value() <= 0:
            QMessageBox.warning(
                self,
                "Błąd",
                "Ilość musi być większa od zera.",
            )
            return

        if self.buy_price_spin.value() <= 0:
            QMessageBox.warning(
                self,
                "Błąd",
                "Cena zakupu musi być większa od zera.",
            )
            return

        self.accept()

    # ========================================================
    # DATA
    # ========================================================

    def get_position(self) -> Position:

        existing = self.position

        return Position(
            id=existing.id if existing else None,
            ticker=self.ticker_edit.text().strip().upper(),
            name=self.name_edit.text().strip(),
            sector=self.sector_edit.text().strip() or None,
            thesis=self.thesis_edit.toPlainText().strip() or None,
            quantity=float(self.quantity_spin.value()),
            buy_price=float(self.buy_price_spin.value()),
            current_price=(existing.current_price if existing else None),
            buy_date=self.buy_date_edit.date().toString("yyyy-MM-dd"),
            review_date=self.review_date_edit.date().toString("yyyy-MM-dd"),
            currency=self.currency_combo.currentText(),
            sell_threshold_gain=(existing.sell_threshold_gain if existing else 0.20),
            sell_threshold_profit=(
                existing.sell_threshold_profit if existing else 0.10
            ),
            sell_threshold_loss=(existing.sell_threshold_loss if existing else -0.10),
            status=(existing.status if existing else PositionStatus.OPEN),
        )
