# Pakiet danych fundamentalnych — wersja 1

Format dla AI przygotowującej dane. Import: **Historia fundamentalna / import
JSON** w głównym oknie albo **Historia spółki / import JSON / wybór danych**
w rewizji. Najpierw podgląd, potem potwierdzenie. Nie ma automatycznego zapisu
rewizji ani aktualizacji notowań. AI działa poza aplikacją.

## Przykład i zakres

Kompletny przykład: [`../examples/fundamentals-v1.json`](../examples/fundamentals-v1.json).
Wszystkie liczby, emitent i ISIN-y ZZ w przykładzie są **syntetyczne**, nie
stanowią danych FME, DTG, HEN ani VPK. ISIN-y demonstracyjne mają poprawną
cyfrę kontrolną, ale nie są potwierdzone w rejestrze instrumentów.

JSON UTF-8, maks. 5 MB, jeden emitent i 1–10000 obserwacji na pakiet.
`schema_version` to liczba całkowita `1`. Inne wersje, dodatkowe pola,
powtórzone klucze JSON, NaN i Infinity są odrzucane. Liczby są liczbami JSON,
bez przecinka dziesiętnego, separatorów tysięcy i symbolu procentu.

## Struktura główna

| Pole | Znaczenie |
| --- | --- |
| `schema_version` | `1` |
| `issuer` | Obiekt z `id` i `name` |
| `instruments` | Niepusta lista instrumentów jawnie przypisanych emitentowi |
| `observations` | Lista wartości dla różnych metryk i okresów |

`issuer.id`: `lei:<20 znaków A-Z/0-9>` albo `isin:<główny ISIN emitenta>`.
Drugi wariant jest stabilnym lokalnym kluczem grupowania, a nie stwierdzeniem,
że spółka jest instrumentem. Przy następnych pakietach używaj tego samego
identyfikatora. Aplikacja sprawdza składnię LEI, nie jego prawdziwość.
ISIN jest normalizowany do wielkich liter i sprawdzany algorytmem cyfry
kontrolnej. Zewnętrznej relacji emitent–instrument nie sprawdzamy automatycznie.

Każdy instrument ma wymagane `isin`, `share_class` (opis klasy) i `currency`
(kod z istniejącego katalogu walut aplikacji, np. EUR) oraz opcjonalny `ticker` (tekst lub null).
Ticker jest informacją prezentacyjną. Istniejące przypisanie ISIN do innego
emitenta, klasy lub waluty oraz konflikt z walutą istniejącej pozycji blokuje
pakiet. Przy dodawaniu nowej klasy sprawdź jej rzeczywistą przynależność.
Można importować spółkę bez jakiejkolwiek pozycji w portfelu.

## Każda obserwacja — wszystkie poniższe pola są wymagane

| Pole | Typ i reguła |
| --- | --- |
| `metric` | Jedna z metryk opisanych poniżej |
| `scope` | `company` lub `instrument` |
| `isin` | Dla company: null; dla instrument: ISIN obecny w instruments |
| `period` | Obiekt: `start`, `end` (RRRR-MM-DD), `basis` |
| `valuation_date` | Data ceny/wyceny lub null; obowiązkowa dla P/E i yield |
| `published_on` | Data udostępnienia **tej wersji wartości**, lub null z wyjaśnieniem |
| `value` | Skończona liczba w zakresie ±10^15 lub null |
| `unit` | `ratio`, `percent` albo `currency`, zgodnie z metryką |
| `currency` | Kod waluty lub null; dla instrumentu zgodny z jego currency |
| `definition` | Niepusty opis wzoru, zakresu i konwencji wskaźnika |
| `source` | Obiekt: niepuste `name`, `url` http(s), `locator` (strona/tabela lub null) |
| `calculation` | Metoda i wejścia obliczenia lub null, gdy wartość podano bezpośrednio |
| `missing_reason` | Wyjaśnienie dla value:null; dla liczby obowiązkowo null |
| `uncertainty` | Opis zastrzeżeń lub null; wymagany przy published_on:null |

`period.basis`: `annual`, `quarter`, `ttm` lub `instant`. Dla instant początek
i koniec są tą samą datą. Pozostałe okresy muszą mieć start <= end. Basis to
deklaracja źródła, nie automatycznie rozpoznany okres. Nie porównuj stubów
sprawozdawczych z pełnym rokiem bez wyjaśnienia definicji.

**Daty są odrębne.** Raport za 2024 zakończony 2024-12-31 może zostać
opublikowany 2025-03-15. Nie używaj końca roku jako daty publikacji.
`published_on` musi uwzględnić najpóźniejsze udostępnienie wszystkich wejść,
w tym ceny. Nie może poprzedzać końca okresu lub valuation_date.
Jeśli wyliczasz historyczny wskaźnik z później opublikowanego raportu, nie był
on znany w dniu dawnej ceny. Podaj faktyczną datę dostępności informacji.

Przy korekcie raportu użyj daty publikacji **korekty**, a nie pierwotnego raportu.
Gdy nie można ustalić dostępności tej wersji danych, wpisz null i uncertainty.
Takie obserwacje pozostają w historii, ale nie kwalifikują się do materiału
datowanej rewizji. Rewizja nie przyjmuje informacji opublikowanych później.
Nie obsługujemy prognoz/forward ani przyszłych okresów jako danych raportowanych.

## Metryki, jednostki i definicje

| metric | unit | Zakres |
| --- | --- | --- |
| pe_ratio | ratio | instrument; obowiązkowa data wyceny i waluta |
| dividend_yield | percent | instrument; obowiązkowa data wyceny i waluta |
| debt_to_equity | ratio | jawnie company albo instrument |
| roe | percent | jawnie company albo instrument |
| payout_ratio | percent | jawnie company albo instrument |
| revenue_growth_3y | percent | jawnie company albo instrument |
| revenue | currency | company; obowiązkowa waluta, pełne jednostki |

`percent`: 15 oznacza **15%**, a nie 0.15. `ratio`: 1.5 oznacza 1.5×,
nie 150%. Przychody w milionach należy przeliczyć na pełne jednostki,
opisując przeliczenie w calculation. Wartości ujemne są dozwolone. Brak
nie jest zerem. Nieistniejący ekonomicznie wskaźnik (np. nieinterpretowalne
P/E przy stracie) może być null z wyjaśnieniem; nie wymyślaj dodatniego P/E.

Nie narzucamy jednej zewnętrznej metodologii dostawcy. `definition` musi
określać np. zysk podstawowy/rozwodniony, dług oprocentowany/zobowiązania,
średni/końcowy kapitał, CAGR i jego lata bazowe oraz trailing/indicated yield.
**Powtarzaj dokładnie tę samą definicję dla jednej porównywalnej serii.**
Jeżeli zmienia się metodologia, zmień definition. Aplikacja nie uzna takiej
serii za automatycznie porównywalną. `calculation` opisuje konkretne wejścia,
daty, źródła i rachunek; nie jest wykonywanym kodem ani formułą do eval.

Nie trzeba dostarczyć wszystkich metryk. Brak pola obserwacji to brak
kompletności obiektu (błąd), brak całej metryki to brak jej dostarczenia
(ostrzeżenie o pokryciu). Zbadany, lecz niedostępny wskaźnik zapisz jako
osobną obserwację z value:null i missing_reason.

## Powtórzenia, korekty i rewizje

Odcisk znormalizowanej treści obserwacji obejmuje emitenta i wszystkie pola
obserwacji. Nazwa pliku, kolejność kluczy/wierszy i zapis 10 vs 10.0 nie mają
znaczenia. Powtórzenia są pomijane, także gdy zaimportowano już nowszą korektę.

Ten sam emitent, scope, ISIN, metric, period, valuation_date, definition,
unit i currency wyznaczają klucz obserwacji. Inna treść dla tego klucza
jest pokazywana jako **korekta** i po potwierdzeniu tworzy nową wersję.
Nie aktualizuje starego wiersza. Dwie różne wersje klucza w jednym pakiecie
są odrzucane jako niejednoznaczne.

Użytkownik może wybrać kilka okresów jako materiał rewizji. Dla metryk
formularza wybierana jest najnowsza wartość z zaznaczonej zgodnej serii,
z jawnym zachowaniem braków. Dla różnych definicji wymagany jest ręczny wybór
jednej serii. Przychody są kontekstem historycznym, nie dodatkowym polem Review.
Tylko zaznaczone dane są kopiowane do rewizji. Można zaznaczyć cały widoczny
kontekst jednym przyciskiem, aby zachować także analizowane wcześniejsze lata.
Pola formularza pokazują osiem miejsc po przecinku; niezmieniony import
zachowuje pełną pierwotną wartość. Ręczna zmiana jest oznaczona w kopii rewizji.

## Polecenie dla kolejnego AI

„Przygotuj pakiet zgodny z FUNDAMENTALS_JSON.md v1 dla wskazanego emitenta,
ISIN i zakresu lat. Najpierw potwierdź instrument i klasę akcji. Korzystaj
z raportów lub jawnie opisanych danych źródłowych. Podaj dokładne URL,
lokalizację w raporcie, okresy, daty udostępnienia i definicje. Przy obliczeniach
pokaż metodę i wejścia. Zaznacz null i powód braków. Nie zgaduj dawnych
motywacji inwestora ani dat publikacji. Nie twórz rewizji ani transakcji.
Przykład zawiera dane syntetyczne — nie kopiuj jego wartości do prawdziwej spółki.”
