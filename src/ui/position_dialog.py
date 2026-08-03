from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QDate, QRegularExpression, Qt
from PySide6.QtGui import QDoubleValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    DEFAULT_CURRENCY,
    DEFAULT_SELL_THRESHOLD_GAIN,
    DEFAULT_SELL_THRESHOLD_LOSS,
    DEFAULT_SELL_THRESHOLD_PROFIT,
    DISPLAY_DATE_FORMAT,
    REVIEW_INTERVAL_DAYS,
    STATUS_OPEN,
    SUPPORTED_CURRENCIES,
)
from src.models import Position


def iso_to_qdate(value: str) -> QDate:
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    return QDate(parsed.year, parsed.month, parsed.day)


def qdate_to_iso(value: QDate) -> str:
    return date(value.year(), value.month(), value.day()).isoformat()


class PositionDialog(QDialog):
    def __init__(
        self, position: Position | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.position = position
        self.setModal(True)
        self.setWindowTitle("Edytuj pozycję" if position else "Dodaj pozycję")
        self.resize(560, 620)
        self._build_ui()
        self._connect_signals()
        if position is not None:
            self._load_position(position)
        else:
            self._set_defaults()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.ticker_edit = QLineEdit()
        self.ticker_edit.setMaxLength(10)
        self.ticker_edit.setPlaceholderText("np. HEN")
        self.ticker_edit.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"[A-Za-z0-9.\-]{1,10}"), self
            )
        )

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Pełna nazwa spółki lub instrumentu")

        self.sector_edit = QLineEdit()
        self.sector_edit.setPlaceholderText("np. Akcje / Healthcare")

        self.buy_price_spin = QDoubleSpinBox()
        self.buy_price_spin.setDecimals(4)
        self.buy_price_spin.setRange(0.0001, 999999.99)
        self.buy_price_spin.setSingleStep(0.1)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(SUPPORTED_CURRENCIES)

        self.buy_date_edit = QDateEdit()
        self.buy_date_edit.setCalendarPopup(True)
        self.buy_date_edit.setDisplayFormat(DISPLAY_DATE_FORMAT)

        review_date_row = QHBoxLayout()
        self.review_date_edit = QDateEdit()
        self.review_date_edit.setCalendarPopup(True)
        self.review_date_edit.setDisplayFormat(DISPLAY_DATE_FORMAT)
        self.plus_year_button = QPushButton("+1 rok")
        review_date_row.addWidget(self.review_date_edit, 1)
        review_date_row.addWidget(self.plus_year_button)
        review_date_widget = QWidget()
        review_date_widget.setLayout(review_date_row)

        form.addRow("Ticker *", self.ticker_edit)
        form.addRow("Nazwa *", self.name_edit)
        form.addRow("Sektor", self.sector_edit)
        form.addRow("Cena zakupu *", self.buy_price_spin)
        form.addRow("Waluta", self.currency_combo)
        form.addRow("Data zakupu *", self.buy_date_edit)
        form.addRow("Data rewizji *", review_date_widget)
        main_layout.addLayout(form)

        thresholds_group = QGroupBox("Progi decyzyjne")
        thresholds_layout = QFormLayout(thresholds_group)
        self.profit_threshold_spin = self._pct_spin(0.0, 100.0)
        self.gain_threshold_spin = self._pct_spin(0.0, 100.0)
        self.loss_threshold_spin = self._pct_spin(-100.0, 0.0)
        thresholds_layout.addRow("ZAROBEK ≥", self.profit_threshold_spin)
        thresholds_layout.addRow("RZUCAM SZTABKAMI ≥", self.gain_threshold_spin)
        thresholds_layout.addRow("NEGATYWNY <", self.loss_threshold_spin)
        main_layout.addWidget(thresholds_group)

        self.thesis_edit = QTextEdit()
        self.thesis_edit.setPlaceholderText("Dlaczego kupiłem? Teza inwestycyjna...")
        self.thesis_edit.setMinimumHeight(120)
        main_layout.addWidget(QLabel("Teza inwestycyjna"))
        main_layout.addWidget(self.thesis_edit, 1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Zapisz")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        main_layout.addWidget(self.button_box)

    def _connect_signals(self) -> None:
        self.ticker_edit.textChanged.connect(self._uppercase_ticker)
        self.plus_year_button.clicked.connect(self._set_review_plus_year)
        self.button_box.accepted.connect(self._try_accept)
        self.button_box.rejected.connect(self.reject)

    def _pct_spin(self, minimum: float, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(minimum, maximum)
        spin.setSuffix(" %")
        spin.setSingleStep(1.0)
        return spin

    def _set_defaults(self) -> None:
        today = QDate.currentDate()
        self.buy_date_edit.setDate(today)
        self.review_date_edit.setDate(today.addDays(REVIEW_INTERVAL_DAYS))
        self.currency_combo.setCurrentText(DEFAULT_CURRENCY)
        self.profit_threshold_spin.setValue(DEFAULT_SELL_THRESHOLD_PROFIT * 100)
        self.gain_threshold_spin.setValue(DEFAULT_SELL_THRESHOLD_GAIN * 100)
        self.loss_threshold_spin.setValue(DEFAULT_SELL_THRESHOLD_LOSS * 100)

    def _load_position(self, position: Position) -> None:
        self.ticker_edit.setText(position.ticker)
        self.ticker_edit.setEnabled(False)
        self.name_edit.setText(position.name)
        self.sector_edit.setText(position.sector or "")
        self.buy_price_spin.setValue(position.buy_price)
        self.currency_combo.setCurrentText(position.currency)
        self.buy_date_edit.setDate(iso_to_qdate(position.buy_date))
        self.review_date_edit.setDate(iso_to_qdate(position.review_date))
        self.profit_threshold_spin.setValue(position.sell_threshold_profit * 100)
        self.gain_threshold_spin.setValue(position.sell_threshold_gain * 100)
        self.loss_threshold_spin.setValue(position.sell_threshold_loss * 100)
        self.thesis_edit.setPlainText(position.thesis or "")

    def _uppercase_ticker(self, text: str) -> None:
        upper = text.upper()
        if text != upper:
            cursor = self.ticker_edit.cursorPosition()
            self.ticker_edit.blockSignals(True)
            self.ticker_edit.setText(upper)
            self.ticker_edit.setCursorPosition(cursor)
            self.ticker_edit.blockSignals(False)

    def _set_review_plus_year(self) -> None:
        self.review_date_edit.setDate(
            self.buy_date_edit.date().addDays(REVIEW_INTERVAL_DAYS)
        )

    def _try_accept(self) -> None:
        if self._validate():
            self.accept()

    def _validate(self) -> bool:
        valid = True
        for widget in (self.ticker_edit, self.name_edit):
            is_empty = not widget.text().strip()
            self._mark_error(widget, is_empty)
            valid = valid and not is_empty

        if self.buy_date_edit.date() > self.review_date_edit.date():
            self._mark_error(self.review_date_edit, True)
            QMessageBox.warning(
                self,
                "Walidacja",
                "Data rewizji nie może być wcześniejsza niż data zakupu.",
            )
            return False
        self._mark_error(self.review_date_edit, False)

        profit = self.profit_threshold_spin.value()
        gain = self.gain_threshold_spin.value()
        loss = self.loss_threshold_spin.value()
        if not (loss < 0 < profit < gain):
            QMessageBox.warning(
                self,
                "Walidacja progów",
                "Progi muszą spełniać warunek: NEGATYWNY < 0 < ZAROBEK < RZUCAM SZTABKAMI.",
            )
            valid = False
        return valid

    def _mark_error(self, widget: QWidget, state: bool) -> None:
        if state:
            widget.setStyleSheet("border: 1px solid #FF6B6B;")
        else:
            widget.setStyleSheet("")

    def get_position(self) -> Position:
        status = self.position.status if self.position else STATUS_OPEN
        current_price = self.position.current_price if self.position else None
        position_id = self.position.id if self.position else None
        return Position(
            id=position_id,
            ticker=self.ticker_edit.text().strip().upper(),
            name=self.name_edit.text().strip(),
            sector=self.sector_edit.text().strip() or None,
            thesis=self.thesis_edit.toPlainText().strip() or None,
            buy_price=self.buy_price_spin.value(),
            buy_date=qdate_to_iso(self.buy_date_edit.date()),
            review_date=qdate_to_iso(self.review_date_edit.date()),
            currency=self.currency_combo.currentText(),
            sell_threshold_gain=self.gain_threshold_spin.value() / 100,
            sell_threshold_profit=self.profit_threshold_spin.value() / 100,
            sell_threshold_loss=self.loss_threshold_spin.value() / 100,
            status=status,
            current_price=current_price,
        )
