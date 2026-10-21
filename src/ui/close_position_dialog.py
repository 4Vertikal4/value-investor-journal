from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.config import DISPLAY_DATE_FORMAT, STATUS_CLOSED
from src.models import Position, PositionValuation
from src.rule_engine import format_return


def qdate_to_iso(value: QDate) -> str:
    return date(value.year(), value.month(), value.day()).isoformat()


class ClosePositionDialog(QDialog):
    """Collect closing terms; MainWindow remains responsible for persistence."""

    def __init__(
        self, position: Position, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        if position.status == STATUS_CLOSED or position.quantity <= 0:
            raise ValueError("Można zamknąć wyłącznie otwartą pozycję.")
        self.position = position
        self.setWindowTitle(f"Zamknij pozycję {position.ticker}")
        self.setModal(True)
        self.resize(420, 260)
        self._build_ui()
        self._update_result()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Ticker", QLabel(self.position.ticker))
        form.addRow("Ilość", QLabel(str(self.position.quantity)))
        form.addRow(
            "Średni koszt",
            QLabel(f"{self.position.average_cost:.4f} {self.position.currency}"),
        )
        current_price = (
            f"{self.position.current_price:.4f} {self.position.currency}"
            if self.position.current_price is not None
            else "Brak ceny"
        )
        form.addRow("Aktualna cena", QLabel(current_price))

        self.sell_price_spin = QDoubleSpinBox()
        self.sell_price_spin.setDecimals(4)
        self.sell_price_spin.setRange(0.0001, 999999999.99)
        self.sell_price_spin.setSingleStep(0.1)
        self.sell_price_spin.setSuffix(f" {self.position.currency}")
        self.sell_price_spin.setValue(
            self.position.current_price or self.position.average_cost
        )
        form.addRow("Cena sprzedaży", self.sell_price_spin)

        self.sell_date_edit = QDateEdit()
        self.sell_date_edit.setCalendarPopup(True)
        self.sell_date_edit.setDisplayFormat(DISPLAY_DATE_FORMAT)
        self.sell_date_edit.setDate(QDate.currentDate())
        form.addRow("Data sprzedaży", self.sell_date_edit)

        self.realized_return_label = QLabel("—")
        form.addRow("Zrealizowany zwrot", self.realized_return_label)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Zamknij pozycję"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.sell_price_spin.valueChanged.connect(self._update_result)

    def _update_result(self, _value: float = 0.0) -> None:
        realized_return = PositionValuation.realized_return(
            self.position, self.sell_price_spin.value()
        )
        color = "#90EE90" if realized_return >= 0 else "#FF6B6B"
        self.realized_return_label.setText(format_return(realized_return))
        self.realized_return_label.setStyleSheet(
            f"color: {color}; font-weight: bold;"
        )

    def _try_accept(self) -> None:
        if self.sell_price_spin.value() <= 0:
            QMessageBox.warning(
                self, "Walidacja", "Cena sprzedaży musi być większa od zera."
            )
            return
        self.accept()

    @property
    def sell_price(self) -> float:
        return self.sell_price_spin.value()

    @property
    def sell_date(self) -> str:
        return qdate_to_iso(self.sell_date_edit.date())
