# Dziennik Inwestora Value

Copyright © 2026 Tomasz Kopek

This project is licensed under the PolyForm Noncommercial License 1.0.0.

See the [LICENSE](LICENSE) file for details.

---

## 1. O aplikacji

Dziennik Inwestora Value to natywna aplikacja desktopowa dla inwestora długoterminowego stosującego podejście value investing.

Aplikacja służy do prowadzenia i okresowej oceny portfela inwestycyjnego. Pozwala dokumentować decyzje inwestycyjne, monitorować pozycje, analizować podstawowe wskaźniki fundamentalne oraz kontrolować alokację aktywów.

**To dziennik inwestora, a nie system transakcyjny ani terminal giełdowy.**

Aplikacja nie prowadzi pełnego rejestru wszystkich transakcji i nie pobiera automatycznie bieżących notowań rynkowych.

Dane przechowywane są lokalnie w bazie SQLite.

## 2. Główne funkcje

**Pozycje inwestycyjne**
- Dodawanie i edycja pozycji.
- Cena zakupu, ilość i średni koszt posiadania.
- Teza inwestycyjna i progi decyzyjne.
- Bieżąca cena rynkowa i wycena pozycji.

**Rewizje inwestycyjne**
- Okresowa ocena pozycji.
- Zapisywanie ceny, zwrotu i kategorii.
- Instrukcja decyzyjna.
- Historia rewizji i metryki fundamentalne.

**Metryki fundamentalne**
- P/E ratio.
- Dividend yield.
- D/E ratio.
- ROE.
- Payout ratio.
- Revenue growth 3Y.
- Porównywanie zmian wskaźników w czasie.
- Odrębna historia danych fundamentalnych ze źródłami, definicjami i datami.
- Import wersjonowanych pakietów JSON przygotowanych przez AI: podgląd,
  kontrola instrumentu i jawne zatwierdzenie. Powtórzenia są pomijane,
  korekty zachowują poprzednie wersje.
- W rewizji można wybrać dane historyczne lub nadal wpisywać metryki ręcznie.
  Rewizja zachowuje kopię użytych danych; import nie tworzy rewizji i nie
  zmienia jej terminu. Data analizy pozostaje datą faktycznej oceny inwestora.
- Wskaźniki z Lightyear mogą łączyć aktualną cenę rynkową z wynikami TTM lub CAGR. Data odczytu nie oznacza, że takie same wartości były znane w dniu zakupu.

**Alokacja aktywów**
- Podział portfela według kategorii.
- Cele alokacji i aktualny udział aktywów.
- Różnice pomiędzy alokacją docelową i rzeczywistą.
- Strategiczny przegląd portfela.

**Import i eksport**
- Import operacji z plików CSV Lightyear.
- Eksport danych do XLSX i CSV.
- Tworzenie kopii bazy SQLite.

## 3. Pierwsze uruchomienie

Przy pierwszym uruchomieniu aplikacja automatycznie tworzy lokalną bazę danych:

`data/dziennik.db`

Baza jest początkowo pusta. Aplikacja nie dodaje automatycznie przykładowych spółek ani pozycji inwestycyjnych.

Pracę można rozpocząć na dwa sposoby:

- **+ Dodaj** — ręczne wprowadzenie pierwszej pozycji inwestycyjnej.
- **Import CSV** — zaimportowanie danych z wyciągu Lightyear.

Po dodaniu pozycji można uzupełnić jej aktualną cenę rynkową, a następnie korzystać z funkcji rewizji i oceny inwestycji.

## 4. Ważne informacje o imporcie Lightyear

Importer identyfikuje instrumenty według ISIN.

Aplikacja zabezpiecza się przed ponownym zaimportowaniem pliku o identycznej zawartości. Wykorzystuje do tego skrót SHA-256 pliku.

Należy pamiętać, że:
- zmiana zawartości pliku powoduje potraktowanie go jako nowego importu;
- dwa różne eksporty mogą zawierać te same operacje;
- aplikacja nie rozpoznaje automatycznie nakładających się transakcji pomiędzy różnymi eksportami.

**Nie należy ponownie importować kolejnych eksportów bez sprawdzenia, czy nie zawierają już wcześniej zaimportowanych operacji.**

Importer nie zastępuje pełnego rejestru transakcji.

## 5. Wymagania

- Python 3.12 lub nowszy.
- Linux (rekomendowane środowisko: KDE Plasma).
- Pakiety wymienione w `requirements.txt`.

Aplikacja wykorzystuje PySide6 i Qt6.

## 6. Instalacja i uruchomienie

W terminalu:

```bash
cd value-investor-journal

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python main.py
```

## 7. Struktura projektu

```text
value-investor-journal/
├── assets/
│   └── icons/
├── data/
├── docs/
│   ├── DESIGN_DECISIONS.md
│   ├── FUNDAMENTALS_JSON.md
│   └── USER_GUIDE.md
├── examples/
│   └── fundamentals-v1.json
├── imports/
├── src/
│   ├── __init__.py
│   ├── asset_engine.py
│   ├── config.py
│   ├── currencies.py
│   ├── data_provider.py
│   ├── database.py
│   ├── exporter.py
│   ├── fundamentals.py
│   ├── importer_lightyear.py
│   ├── metrics_engine.py
│   ├── models.py
│   ├── notification_service.py
│   ├── rule_engine.py
│   └── ui/
│       ├── __init__.py
│       ├── asset_allocation_widget.py
│       ├── close_position_dialog.py
│       ├── dashboard_table.py
│       ├── fundamentals_dialog.py
│       ├── main_window.py
│       ├── position_dialog.py
│       ├── review_dialog.py
│       └── styles.py
├── tests/
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_fundamentals.py
│   ├── test_importer_lightyear.py
│   ├── test_metrics_engine.py
│   └── test_rule_engine.py
├── main.py
├── requirements.txt
└── README.md
```

## 8. Dokumentacja projektowa

- [Instrukcja użytkownika](docs/USER_GUIDE.md)
- [Decyzje projektowe](docs/DESIGN_DECISIONS.md)
- [Format JSON dla AI i przykład](docs/FUNDAMENTALS_JSON.md)

Historia fundamentalna i import JSON są dostępne z paska narzędzi oraz
formularza rewizji. Dwuklik wpisu w historii rewizji pokazuje notatki inwestora
i zachowany materiał źródłowy. Dane opublikowane po dacie analizy lub z nieznaną
datą publikacji nie mogą być dołączone jako potwierdzony materiał tej rewizji.

Dokumentacja decyzji projektowych opisuje przyjęte założenia architektoniczne, źródła prawdy w modelu danych, świadome ograniczenia oraz uzasadnienie zastosowanych rozwiązań.

## 9. Dodatkowe informacje

- Kolorowanie pozycji i trendów metryk pomaga w ocenie portfela.
- Aplikacja udostępnia ikonę zasobnika systemowego z przypomnieniami o terminach rewizji.
- Automatyczne pobieranie metryk fundamentalnych nie jest obecnie dostępne.
