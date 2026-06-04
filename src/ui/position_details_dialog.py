from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)

from src.models import Position


class PositionDetailsDialog(QDialog):
    def __init__(
        self,
        position: Position,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.position = position

        self.setWindowTitle(
            f"{position.ticker} - Szczegóły pozycji"
        )

        self.setMinimumWidth(700)

        self._build_ui()

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)

        form = QFormLayout()

        form.addRow("Ticker", QLabel(self.position.ticker))
        form.addRow("Nazwa", QLabel(self.position.name))
        form.addRow("Sektor", QLabel(self.position.sector or "-"))

        form.addRow("Ilość", QLabel(str(self.position.quantity)))

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

        thesis.setPlainText(
            self.position.thesis or ""
        )

        thesis.setMinimumHeight(150)

        layout.addWidget(thesis)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Close
        )

        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout.addWidget(buttons)
