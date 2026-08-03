# Dziennik Inwestora Value

Natywna aplikacja desktopowa PySide6/Qt6 dla value investora:
lokalny dziennik pozycji, rewizje, metryki fundamentalne,
reguły decyzyjne, alokacja aktywów, import CSV Lightyear
i eksport XLSX/CSV.

## Wymagania

- Python 3.12+
- Linux/KDE Plasma rekomendowany,
  ale aplikacja używa standardowych widgetów Qt6.
- Pakiety z requirements.txt

## Uruchomienie

```bash
cd value-investor-journal
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

Przy pierwszym uruchomieniu powstanie baza:
data/dziennik.db
oraz demo dane:
HEN, DTG, FME i kategorie aktywów.

## Struktura

```text
value-investor-journal/
├── data/
├── imports/
├── assets/icons/
├── src/
│   ├── main.py
│   ├── database.py
│   ├── rule_engine.py
│   ├── metrics_engine.py
│   ├── asset_engine.py
│   ├── importer_lightyear.py
│   ├── exporter.py
│   ├── notification_service.py
│   └── ui/
└── tests/
```

## Najważniejsze funkcje

Pozycje:
cena zakupu, teza, progi rewizji,
status i ocena aktualna.

Rewizje:
cena, zwrot, kategoria,
instrukcja oraz sesja metryk fundamentalnych.

Kolorowanie trendów metryk:
zielony, żółty, czerwony, szary.

Dashboard:
kolorowanie wierszy według trendu,
roczna histogramy / trendy.

Alokacja aktywów:
wykres kołowy + tabela target/actual/delta.

Tray icon z przypomnieniami o terminach rewizji.

Eksport XLSX/CSV z backup bazy SQLite.
