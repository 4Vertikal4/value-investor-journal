from __future__ import annotations

import unicodedata


# Snapshot of ISO 4217 List One published by the SIX maintenance agency.
# Verified 2026-10-06; 178 unique current currency, fund and metal codes.
ISO_4217_CURRENCIES: tuple[tuple[str, str], ...] = (
    ("AED", "UAE Dirham"),
    ("AFN", "Afghani"),
    ("ALL", "Lek"),
    ("AMD", "Armenian Dram"),
    ("AOA", "Kwanza"),
    ("ARS", "Argentine Peso"),
    ("AUD", "Australian Dollar"),
    ("AWG", "Aruban Florin"),
    ("AZN", "Azerbaijan Manat"),
    ("BAM", "Convertible Mark"),
    ("BBD", "Barbados Dollar"),
    ("BDT", "Taka"),
    ("BHD", "Bahraini Dinar"),
    ("BIF", "Burundi Franc"),
    ("BMD", "Bermudian Dollar"),
    ("BND", "Brunei Dollar"),
    ("BOB", "Boliviano"),
    ("BOV", "Mvdol"),
    ("BRL", "Brazilian Real"),
    ("BSD", "Bahamian Dollar"),
    ("BTN", "Ngultrum"),
    ("BWP", "Pula"),
    ("BYN", "Belarusian Ruble"),
    ("BZD", "Belize Dollar"),
    ("CAD", "Canadian Dollar"),
    ("CDF", "Congolese Franc"),
    ("CHE", "WIR Euro"),
    ("CHF", "Swiss Franc"),
    ("CHW", "WIR Franc"),
    ("CLF", "Unidad de Fomento"),
    ("CLP", "Chilean Peso"),
    ("CNY", "Yuan Renminbi"),
    ("COP", "Colombian Peso"),
    ("COU", "Unidad de Valor Real"),
    ("CRC", "Costa Rican Colon"),
    ("CUP", "Cuban Peso"),
    ("CVE", "Cabo Verde Escudo"),
    ("CZK", "Czech Koruna"),
    ("DJF", "Djibouti Franc"),
    ("DKK", "Danish Krone"),
    ("DOP", "Dominican Peso"),
    ("DZD", "Algerian Dinar"),
    ("EGP", "Egyptian Pound"),
    ("ERN", "Nakfa"),
    ("ETB", "Ethiopian Birr"),
    ("EUR", "Euro"),
    ("FJD", "Fiji Dollar"),
    ("FKP", "Falkland Islands Pound"),
    ("GBP", "Pound Sterling"),
    ("GEL", "Lari"),
    ("GHS", "Ghana Cedi"),
    ("GIP", "Gibraltar Pound"),
    ("GMD", "Dalasi"),
    ("GNF", "Guinean Franc"),
    ("GTQ", "Quetzal"),
    ("GYD", "Guyana Dollar"),
    ("HKD", "Hong Kong Dollar"),
    ("HNL", "Lempira"),
    ("HTG", "Gourde"),
    ("HUF", "Hungarian Forint"),
    ("IDR", "Rupiah"),
    ("ILS", "New Israeli Sheqel"),
    ("INR", "Indian Rupee"),
    ("IQD", "Iraqi Dinar"),
    ("IRR", "Iranian Rial"),
    ("ISK", "Iceland Krona"),
    ("JMD", "Jamaican Dollar"),
    ("JOD", "Jordanian Dinar"),
    ("JPY", "Yen"),
    ("KES", "Kenyan Shilling"),
    ("KGS", "Som"),
    ("KHR", "Riel"),
    ("KMF", "Comorian Franc"),
    ("KPW", "North Korean Won"),
    ("KRW", "Won"),
    ("KWD", "Kuwaiti Dinar"),
    ("KYD", "Cayman Islands Dollar"),
    ("KZT", "Tenge"),
    ("LAK", "Lao Kip"),
    ("LBP", "Lebanese Pound"),
    ("LKR", "Sri Lanka Rupee"),
    ("LRD", "Liberian Dollar"),
    ("LSL", "Loti"),
    ("LYD", "Libyan Dinar"),
    ("MAD", "Moroccan Dirham"),
    ("MDL", "Moldovan Leu"),
    ("MGA", "Malagasy Ariary"),
    ("MKD", "Denar"),
    ("MMK", "Kyat"),
    ("MNT", "Tugrik"),
    ("MOP", "Pataca"),
    ("MRU", "Ouguiya"),
    ("MUR", "Mauritius Rupee"),
    ("MVR", "Rufiyaa"),
    ("MWK", "Malawi Kwacha"),
    ("MXN", "Mexican Peso"),
    ("MXV", "Mexican Unidad de Inversion (UDI)"),
    ("MYR", "Malaysian Ringgit"),
    ("MZN", "Mozambique Metical"),
    ("NAD", "Namibia Dollar"),
    ("NGN", "Naira"),
    ("NIO", "Cordoba Oro"),
    ("NOK", "Norwegian Krone"),
    ("NPR", "Nepalese Rupee"),
    ("NZD", "New Zealand Dollar"),
    ("OMR", "Rial Omani"),
    ("PAB", "Balboa"),
    ("PEN", "Sol"),
    ("PGK", "Kina"),
    ("PHP", "Philippine Peso"),
    ("PKR", "Pakistan Rupee"),
    ("PLN", "Polish Zloty"),
    ("PYG", "Guarani"),
    ("QAR", "Qatari Rial"),
    ("RON", "Romanian Leu"),
    ("RSD", "Serbian Dinar"),
    ("RUB", "Russian Ruble"),
    ("RWF", "Rwanda Franc"),
    ("SAR", "Saudi Riyal"),
    ("SBD", "Solomon Islands Dollar"),
    ("SCR", "Seychelles Rupee"),
    ("SDG", "Sudanese Pound"),
    ("SEK", "Swedish Krona"),
    ("SGD", "Singapore Dollar"),
    ("SHP", "Saint Helena Pound"),
    ("SLE", "Leone"),
    ("SOS", "Somali Shilling"),
    ("SRD", "Surinam Dollar"),
    ("SSP", "South Sudanese Pound"),
    ("STN", "Dobra"),
    ("SVC", "El Salvador Colon"),
    ("SYP", "Syrian Pound"),
    ("SZL", "Lilangeni"),
    ("THB", "Baht"),
    ("TJS", "Somoni"),
    ("TMT", "Turkmenistan New Manat"),
    ("TND", "Tunisian Dinar"),
    ("TOP", "Pa’anga"),
    ("TRY", "Turkish Lira"),
    ("TTD", "Trinidad and Tobago Dollar"),
    ("TWD", "New Taiwan Dollar"),
    ("TZS", "Tanzanian Shilling"),
    ("UAH", "Hryvnia"),
    ("UGX", "Uganda Shilling"),
    ("USD", "US Dollar"),
    ("USN", "US Dollar (Next day)"),
    ("UYI", "Uruguay Peso en Unidades Indexadas (UI)"),
    ("UYU", "Peso Uruguayo"),
    ("UYW", "Unidad Previsional"),
    ("UZS", "Uzbekistan Sum"),
    ("VED", "Bolívar Soberano"),
    ("VES", "Bolívar Soberano"),
    ("VND", "Dong"),
    ("VUV", "Vatu"),
    ("WST", "Tala"),
    ("XAD", "Arab Accounting Dinar"),
    ("XAF", "CFA Franc BEAC"),
    ("XAG", "Silver"),
    ("XAU", "Gold"),
    ("XBA", "Bond Markets Unit European Composite Unit (EURCO)"),
    ("XBB", "Bond Markets Unit European Monetary Unit (E.M.U.-6)"),
    ("XBC", "Bond Markets Unit European Unit of Account 9 (E.U.A.-9)"),
    ("XBD", "Bond Markets Unit European Unit of Account 17 (E.U.A.-17)"),
    ("XCD", "East Caribbean Dollar"),
    ("XCG", "Caribbean Guilder"),
    ("XDR", "SDR (Special Drawing Right)"),
    ("XOF", "CFA Franc BCEAO"),
    ("XPD", "Palladium"),
    ("XPF", "CFP Franc"),
    ("XPT", "Platinum"),
    ("XSU", "Sucre"),
    ("XTS", "Codes specifically reserved for testing purposes"),
    ("XUA", "ADB Unit of Account"),
    ("XXX", "No currency"),
    ("YER", "Yemeni Rial"),
    ("ZAR", "Rand"),
    ("ZMW", "Zambian Kwacha"),
    ("ZWG", "Zimbabwe Gold"),
)

PREFERRED_CURRENCY_CODES = ("PLN", "HUF", "USD", "EUR")
CURRENCY_NAMES = dict(ISO_4217_CURRENCIES)
SUPPORTED_CURRENCIES = PREFERRED_CURRENCY_CODES + tuple(
    code
    for code, _name in ISO_4217_CURRENCIES
    if code not in PREFERRED_CURRENCY_CODES
)
CURRENCY_OPTIONS = tuple(
    (code, CURRENCY_NAMES[code]) for code in SUPPORTED_CURRENCIES
)

# Aliases are search-only. Display labels remain the official English names.
CURRENCY_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "CHF": ("frank", "frank szwajcarski"),
    "CNY": ("juan", "yuan"),
    "CZK": ("korona", "korona czeska"),
    "DKK": ("korona", "korona duńska", "korona dunska"),
    "EUR": ("euro",),
    "GBP": ("funt", "funt brytyjski"),
    "HUF": ("forint", "forint węgierski", "forint wegierski"),
    "ISK": ("korona", "korona islandzka"),
    "JPY": ("jen",),
    "NOK": ("korona", "korona norweska"),
    "PLN": ("złoty", "zloty", "polski złoty", "polski zloty"),
    "SEK": ("korona", "korona szwedzka"),
    "USD": ("dolar", "dolar amerykański", "dolar amerykanski"),
}


def currency_label(code: str) -> str:
    """Return the user-facing label while keeping the code as domain data."""
    normalized_code = code.strip().upper()
    return f"{normalized_code} — {CURRENCY_NAMES[normalized_code]}"


def normalize_currency_search(value: str) -> str:
    """Create a case-insensitive, accent-tolerant search representation."""
    folded = value.casefold().translate(str.maketrans({"ł": "l", "đ": "d"}))
    decomposed = unicodedata.normalize("NFKD", folded)
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


def currency_search_text(code: str) -> str:
    """Return display text plus optional localized aliases for completion."""
    label = currency_label(code)
    aliases = " ".join(CURRENCY_SEARCH_ALIASES.get(code, ()))
    raw = f"{label} {aliases}".strip()
    return f"{raw} {normalize_currency_search(raw)}"


def is_supported_currency(code: str) -> bool:
    return code.strip().upper() in CURRENCY_NAMES
