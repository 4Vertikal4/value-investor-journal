

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QModelIndex, QRegularExpression, QSettings, Qt
from PySide6.QtGui import QRegularExpressionValidator, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
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
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    APP_NAME,
    DEFAULT_CURRENCY,
    DEFAULT_SELL_THRESHOLD_GAIN,
    DEFAULT_SELL_THRESHOLD_LOSS,
    DEFAULT_SELL_THRESHOLD_PROFIT,
    DISPLAY_DATE_FORMAT,
    ORGANIZATION_NAME,
    REVIEW_INTERVAL_DAYS,
    STATUS_OPEN,
)
from src.currencies import (
    CURRENCY_NAMES,
    PREFERRED_CURRENCY_CODES,
    SUPPORTED_CURRENCIES,
    currency_label,
    currency_search_text,
    is_supported_currency,
)
from src.models import Position


CURRENCY_SEARCH_ROLE = int(Qt.ItemDataRole.UserRole) + 1
RECENT_CURRENCIES_KEY = "position_dialog/recent_currencies"
RECENT_CURRENCIES_LIMIT = 8


def iso_to_qdate(value: str) -> QDate:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return QDate.currentDate()
    return QDate(parsed.year, parsed.month, parsed.day)


def qdate_to_iso(value: QDate) -> str:
    return date(value.year(), value.month(), value.day()).isoformat()


class CurrencyCompleter(QCompleter):
    """Match a hidden search key but insert the clean display label."""

    def pathFromIndex(self, index: QModelIndex) -> str:
        value = index.data(Qt.ItemDataRole.DisplayRole)
        return str(value) if value is not None else ""


class PositionDialog(QDialog):
    def __init__(
        self, position: Position | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.position = position
        self._is_setting_values = False
        self._average_cost_linked = False
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

        self.isin_edit = QLineEdit()
        self.isin_edit.setMaxLength(12)
        self.isin_edit.setPlaceholderText("np. DE0005785802")
        self.isin_edit.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"[A-Za-z]{2}[A-Za-z0-9]{9}[0-9]"), self
            )
        )

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Pełna nazwa spółki lub instrumentu")

        self.sector_edit = QLineEdit()
        self.sector_edit.setPlaceholderText("np. Akcje / Healthcare")

        self.initial_buy_price_spin = QDoubleSpinBox()
        self.initial_buy_price_spin.setDecimals(4)
        self.initial_buy_price_spin.setRange(0.0001, 999999.99)
        self.initial_buy_price_spin.setSingleStep(0.1)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 2147483647)

        self.average_cost_spin = QDoubleSpinBox()
        self.average_cost_spin.setDecimals(4)
        self.average_cost_spin.setRange(0.0001, 999999.99)
        self.average_cost_spin.setSingleStep(0.1)

        self.currency_combo = QComboBox()
        self._configure_currency_combo()

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
        form.addRow("ISIN *", self.isin_edit)
        form.addRow("Nazwa", self.name_edit)
        form.addRow("Sektor", self.sector_edit)
        form.addRow("Cena zakupu *", self.initial_buy_price_spin)
        form.addRow("Ilość *", self.quantity_spin)
        form.addRow("Średni koszt *", self.average_cost_spin)
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
        self.initial_buy_price_spin.valueChanged.connect(
            self._on_initial_buy_price_changed
        )
        self.average_cost_spin.valueChanged.connect(self._on_average_cost_changed)
        self.ticker_edit.textChanged.connect(self._uppercase_ticker)
        self.plus_year_button.clicked.connect(self._set_review_plus_year)
        self.button_box.accepted.connect(self._try_accept)
        self.button_box.rejected.connect(self.reject)

    def _configure_currency_combo(self) -> None:
        combo = self.currency_combo
        combo.setModel(QStandardItemModel(combo))
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setMaxVisibleItems(18)
        self._populate_currency_combo()

        completer = CurrencyCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setCompletionRole(CURRENCY_SEARCH_ROLE)
        combo.setCompleter(completer)

        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Wpisz kod lub nazwę waluty")

    def _populate_currency_combo(self) -> None:
        recent = self._recent_currency_codes()
        recent_set = set(recent)
        # Each code appears once: a recent item takes precedence over the
        # preferred section so the popup and completion results stay deduplicated.
        preferred = [
            code for code in PREFERRED_CURRENCY_CODES if code not in recent_set
        ]
        used = recent_set | set(preferred)
        remaining = [
            code for code in SUPPORTED_CURRENCIES if code not in used
        ]

        self._add_currency_group("OSTATNIO UŻYWANE", recent)
        self._add_currency_group("POPULARNE / PREFEROWANE", preferred)
        self._add_currency_group("POZOSTAŁE", remaining)

    def _add_currency_group(self, title: str, codes: list[str]) -> None:
        if not codes:
            return
        combo = self.currency_combo
        if combo.count():
            combo.insertSeparator(combo.count())

        heading_index = combo.count()
        combo.addItem(title)
        model = combo.model()
        if isinstance(model, QStandardItemModel):
            heading = model.item(heading_index)
            if heading is not None:
                heading.setEnabled(False)
                heading.setSelectable(False)

        for code in codes:
            self._add_currency_item(code)

    def _add_currency_item(self, code: str) -> int:
        combo = self.currency_combo
        index = combo.count()
        combo.addItem(currency_label(code), code)
        combo.setItemData(index, currency_search_text(code), CURRENCY_SEARCH_ROLE)
        return index

    @staticmethod
    def _recent_currency_codes() -> list[str]:
        settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        stored = settings.value(RECENT_CURRENCIES_KEY, [])
        values = [stored] if isinstance(stored, str) else list(stored or [])
        recent: list[str] = []
        for value in values:
            code = str(value).strip().upper()
            if code in CURRENCY_NAMES and code not in recent:
                recent.append(code)
        return recent[:RECENT_CURRENCIES_LIMIT]

    def _remember_currency(self, code: str) -> None:
        recent = [item for item in self._recent_currency_codes() if item != code]
        recent.insert(0, code)
        QSettings(ORGANIZATION_NAME, APP_NAME).setValue(
            RECENT_CURRENCIES_KEY,
            recent[:RECENT_CURRENCIES_LIMIT],
        )

    def _select_currency(self, code: str, allow_legacy: bool = False) -> bool:
        normalized = code.strip().upper()
        index = self.currency_combo.findData(normalized)
        if index < 0 and allow_legacy and normalized:
            index = self.currency_combo.count()
            self.currency_combo.insertSeparator(index)
            index = self.currency_combo.count()
            self.currency_combo.addItem(
                f"{normalized} — Existing/legacy currency", normalized
            )
            self.currency_combo.setItemData(
                index,
                normalized,
                CURRENCY_SEARCH_ROLE,
            )
        if index < 0:
            return False
        self.currency_combo.setCurrentIndex(index)
        return True

    def _resolve_currency_code(self) -> str | None:
        combo = self.currency_combo
        entered = combo.currentText().strip()
        current_index = combo.currentIndex()
        if current_index >= 0:
            current_code = combo.itemData(current_index)
            current_label = combo.itemText(current_index)
            if current_code and entered.casefold() == current_label.casefold():
                return str(current_code)

        normalized = entered.upper()
        if is_supported_currency(normalized):
            index = combo.findData(normalized)
            if index >= 0:
                combo.setCurrentIndex(index)
                return normalized

        for index in range(combo.count()):
            code = combo.itemData(index)
            if code and entered.casefold() == combo.itemText(index).casefold():
                combo.setCurrentIndex(index)
                return str(code)
        return None

    def _pct_spin(self, minimum: float, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(minimum, maximum)
        spin.setSuffix(" %")
        spin.setSingleStep(1.0)
        return spin

    def _set_defaults(self) -> None:
        self._is_setting_values = True
        self._average_cost_linked = True

        today = QDate.currentDate()
        self.quantity_spin.setValue(1)
        self.buy_date_edit.setDate(today)
        self.review_date_edit.setDate(today.addDays(REVIEW_INTERVAL_DAYS))
        self.average_cost_spin.setValue(self.initial_buy_price_spin.value())
        self._select_currency(DEFAULT_CURRENCY)
        self.profit_threshold_spin.setValue(DEFAULT_SELL_THRESHOLD_PROFIT * 100)
        self.gain_threshold_spin.setValue(DEFAULT_SELL_THRESHOLD_GAIN * 100)
        self.loss_threshold_spin.setValue(DEFAULT_SELL_THRESHOLD_LOSS * 100)

        self._is_setting_values = False

    def _on_initial_buy_price_changed(self, value: float) -> None:
        if self._is_setting_values:
            return
        if self._average_cost_linked:
            self._is_setting_values = True
            self.average_cost_spin.setValue(value)
            self._is_setting_values = False

    def _on_average_cost_changed(self, value: float) -> None:
        if self._is_setting_values:
            return
        self._average_cost_linked = False

    def _load_position(self, position: Position) -> None:
        self._is_setting_values = True
        self._average_cost_linked = False
        self.ticker_edit.setText(position.ticker)
        self.isin_edit.setText(position.isin)
        self.isin_edit.setEnabled(False)
        self.name_edit.setText(position.name or "")
        self.sector_edit.setText(position.sector or "")
        self.initial_buy_price_spin.setValue(position.initial_buy_price)
        self.initial_buy_price_spin.setEnabled(False)
        self.quantity_spin.setValue(position.quantity)
        self.quantity_spin.setEnabled(False)
        self.average_cost_spin.setValue(position.average_cost)
        self._select_currency(position.currency, allow_legacy=True)
        self.currency_combo.setEnabled(False)
        self.buy_date_edit.setDate(iso_to_qdate(position.initial_buy_date))
        self.buy_date_edit.setEnabled(False)
        self.review_date_edit.setDate(iso_to_qdate(position.review_date))
        self.profit_threshold_spin.setValue(position.sell_threshold_profit * 100)
        self.gain_threshold_spin.setValue(position.sell_threshold_gain * 100)
        self.loss_threshold_spin.setValue(position.sell_threshold_loss * 100)
        self.thesis_edit.setPlainText(position.thesis or "")
        self._is_setting_values = False

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
            currency = self._resolve_currency_code()
            if currency is not None:
                self._remember_currency(currency)
            self.accept()

    def _validate(self) -> bool:
        valid = True
        for widget in (self.ticker_edit, self.isin_edit):
            is_empty = not widget.text().strip()
            self._mark_error(widget, is_empty)
            valid = valid and not is_empty

        if not self.isin_edit.hasAcceptableInput():
            self._mark_error(self.isin_edit, True)
            QMessageBox.warning(
                self,
                "Walidacja ISIN",
                "ISIN musi zawierać 12 znaków: 2 litery, 9 znaków oraz cyfrę kontrolną.",
            )
            return False

        currency = self._resolve_currency_code()
        if currency is None:
            self._mark_error(self.currency_combo, True)
            QMessageBox.warning(
                self,
                "Walidacja waluty",
                "Wybierz walutę z listy lub wpisz jej dokładny kod ISO.",
            )
            return False
        self._mark_error(self.currency_combo, False)

        status = self.position.status if self.position else STATUS_OPEN
        if status == STATUS_OPEN and self.quantity_spin.value() <= 0:
            QMessageBox.warning(
                self,
                "Walidacja ilości",
                "Otwarta pozycja musi mieć co najmniej jedną akcję.",
            )
            return False

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
        currency = self._resolve_currency_code()
        if currency is None:
            raise ValueError("Nie wybrano obsługiwanej waluty ISO 4217.")
        status = self.position.status if self.position else STATUS_OPEN
        current_price = self.position.current_price if self.position else None
        sell_date = self.position.sell_date if self.position else None
        sell_price = self.position.sell_price if self.position else None
        realized_gain = self.position.realized_gain if self.position else None
        position_id = self.position.id if self.position else None
        return Position(
            id=position_id,
            ticker=self.ticker_edit.text().strip().upper(),
            isin=self.isin_edit.text().strip().upper(),
            name=self.name_edit.text().strip() or None,
            sector=self.sector_edit.text().strip() or None,
            thesis=self.thesis_edit.toPlainText().strip() or None,
            initial_buy_price=self.initial_buy_price_spin.value(),
            initial_buy_date=qdate_to_iso(self.buy_date_edit.date()),
            quantity=self.quantity_spin.value(),
            average_cost=self.average_cost_spin.value(),
            review_date=qdate_to_iso(self.review_date_edit.date()),
            currency=currency,
            sell_threshold_gain=self.gain_threshold_spin.value() / 100,
            sell_threshold_profit=self.profit_threshold_spin.value() / 100,
            sell_threshold_loss=self.loss_threshold_spin.value() / 100,
            status=status,
            sell_date=sell_date,
            sell_price=sell_price,
            realized_gain=realized_gain,
            current_price=current_price,
        )
