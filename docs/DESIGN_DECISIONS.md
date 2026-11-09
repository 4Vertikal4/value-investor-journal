# Value Investor Journal — decyzje projektowe po migracji `Position`

## Dane fundamentalne i rzeczywiste rewizje (rozszerzenie 2026-11-08)

- **Decyzja:** obserwacje fundamentalne są odrębną historią, niezależną od
  posiadania akcji. `Position`, reguły Lightyear i rejestr plików pozostają
  zgodne z przekazaną wersją. Nie wprowadzamy `investment_transactions`.
  Powód: historia spółki nie wymaga historii przepływów inwestora.
- **Tożsamość:** pakiet v1 opisuje jednego emitenta, jawnie przypisane ISIN-y
  i klasy akcji. Klucz emitenta to LEI lub `isin:<główny ISIN>` jako lokalny
  identyfikator grupowania. ISIN przechodzi kontrolę formatu i cyfry kontrolnej;
  aplikacja nie weryfikuje zewnętrznie prawnego przypisania LEI/ISIN do emitenta.
  Użytkownik potwierdza je w podglądzie. Konflikt istniejącego przypisania,
  klasy albo waluty zatrzymuje import; ticker nie służy dopasowaniu.
  Metryki spółki są wspólne dla przypisanych klas, metryki instrumentu tylko
  dla jego ISIN. P/E i yield wymagają instrumentu i daty wyceny.
- **Czas:** każda obserwacja rozdziela okres finansowy, datę udostępnienia
  tej konkretnej wersji wartości oraz opcjonalną datę wyceny. Data publikacji
  jest najpóźniejszą datą dostępności wszystkich użytych informacji.
  Nie odtwarzamy jej z końca okresu. Nieznana publikacja jest dozwolona
  z wyjaśnieniem, ale blokuje użycie jako materiału dla datowanej rewizji.
  Historia może być filtrowana według informacji dostępnych w zadanym dniu;
  najnowsza kwalifikująca się wersja wybierana jest dopiero po takim filtrze.
  Daty są deklaracją źródła/AI i wymagają sprawdzenia; aplikacja nie potrafi
  wykryć błędnie podanej daty późniejszego przekształcenia sprawozdania.
- **Wersje i import:** import JSON ma podgląd i jawne zatwierdzenie emitenta,
  klas oraz korekt. Walidacja jest ponawiana pod blokadą zapisu SQLite.
  Cały pakiet jest atomowy. Obserwacje są niezmienne, odcisk znormalizowanej
  treści wykrywa powtórzenia również w innym pliku lub kolejności.
  Zmiana wartości/źródła/niepewności dla tego samego klucza (emitent, zakres,
  ISIN, metryka, okres, data wyceny, definicja, jednostka i waluta) tworzy
  nową wersję z odwołaniem do poprzedniej. Ponowny import starej wersji jej
  nie przywraca. Sprzeczne wersje jednego klucza w jednym pakiecie są błędem.
  Zmiana definicji tworzy osobną serię, której nie porównujemy automatycznie.
  Podgląd zachowuje token planu: równoległa zmiana historii wymaga nowego
  podglądu, zamiast zatwierdzać korekty niewidoczne wcześniej użytkownikowi.
- **Rewizja:** import nie tworzy rewizji i nie dotyka ceny ani terminu pozycji.
  `Review` zachowuje faktyczną datę analizy (domyślnie dzisiaj), notatki i
  kopię pełnych wybranych obserwacji oraz faktycznie użytych wartości pól.
  Ręczna zmiana wartości jest oznaczona jako ręczna; nie udaje danych źródłowych.
  Zapis weryfikuje emitenta/ISIN i dostępność danych na dzień analizy.
  Późniejsze korekty nie zmieniają kopii użytej w starej rewizji.
  Wcześniej wykonana rzeczywista analiza może być wpisana z datą przeszłą;
  nie ma sposobu technicznego potwierdzenia, kiedy użytkownik faktycznie myślał.
  Nie wolno używać tej daty do automatycznego antydatowania historii spółki.
  Zachowany model wyniku korzysta z bieżącego średniego kosztu `Position`;
  wpisanie wcześniej wykonanej rewizji nie odtwarza dawnego stanu posiadania
  ani historycznego kosztu. Formularz informuje o tym przy wcześniejszej dacie.
- **Braki i porównania:** JSON null i puste pola ręczne pozostają brakiem;
  wartości ujemne są dozwolone. Brak porównania nie oznacza „bez zmian”.
  Historia fundamentalna pokazuje neutralny wzrost/spadek między zgodnymi
  seriami. Formularz oddzielnie pokazuje metryki z rzeczywistych rewizji
  oraz wcześniejsze notatki inwestora. Istniejące kategorie/instrukcje
  progowe nadal są automatyczną oceną zwrotu, a nie odtworzeniem starej tezy.
  Porównanie okresowe pomija okresy o różnicy długości >21 dni dla kwartału
  albo >45 dni dla roku/TTM (ochrona przed porównaniem skróconego okresu z
  pełnym). To kontrola podstawowa; zgodność zakresu konsolidacji wymaga
  nadal sprawdzenia definicji przez człowieka.
- **Migracja:** dodajemy dwie tabele i jedną nullable kolumnę `reviews` w
  transakcji. Istniejące rewizje zachowują wszystkie dane i NULL zamiast
  wymyślonego pochodzenia. Nie przebudowujemy `positions`. Migracja jest
  idempotentna; testy używają wyłącznie tymczasowych baz.
- **Granice v1:** sześć dotychczasowych wskaźników oraz przychody; jednostki
  ratio, percent (15 oznacza 15%) i currency w pełnych jednostkach waluty.
  Prognozy i automatyczna normalizacja definicji nie są obsługiwane. Metoda
  obliczenia jest opisem, nie wykonywanym kodem. AI działa poza aplikacją;
  nie dodajemy połączeń z modelami, pobierania danych ani notowań.
  Format i przykład opisano w `FUNDAMENTALS_JSON.md`.
  Waluty są sprawdzane wobec istniejącego lokalnego katalogu aplikacji,
  bez dodawania dostawcy danych. Błędnie zatwierdzone przypisanie emitenta
  nie ma automatycznej operacji scalania/zmiany; zmiana ISIN-klasy lub przejście
  z klucza głównego ISIN na LEI wymaga osobno zaprojektowanej, jawnej korekty.
  Daty przyszłe w pakiecie historycznym są odrzucane. W porównaniu metryk
  zapisanych przy rewizjach inna znana definicja lub mieszanie importu
  z ręcznym źródłem oznacza brak porównania. Dotychczasowe porównanie dwóch
  ręcznych/legacy wartości pozostaje heurystyką z nieustalonymi definicjami.

## Wnioski z testu praktycznego (2026-11-08)

- **Lightyear jako źródło bieżących metryk:** odczyt wskaźników w sekcji Advanced dokumentuje stan widoczny w dniu odczytu. Poszczególne wskaźniki mogą mieć różne podstawy czasowe: aktualną cenę rynkową, wyniki TTM lub wieloletni CAGR. Nie przypisujemy bieżącego zestawu automatycznie do dnia zakupu.
- **Znaczenie automatycznej oceny:** kategoria i instrukcja w rewizji wynikają ze stopy zwrotu oraz progów decyzyjnych pozycji. Metryki fundamentalne dostarczają dodatkowego kontekstu, ale same nie wyznaczają automatycznej instrukcji. Własna ocena i decyzja inwestora pozostają w notatkach rewizji.
- **Test interfejsu:** przetestowano uruchomienie aplikacji, historię fundamentalną, podgląd syntetycznego pakietu JSON, formularz wyboru danych do rewizji oraz zapis rzeczywistej rewizji FME z datą 2026-11-08. Pakiet demonstracyjny nie został zatwierdzony.
- **Test rzeczywistych danych FME (2026-11-09):** zaimportowano dwie
  obserwacje przychodów Grupy: Q3 2025 — 4 885 mln EUR, opublikowane
  2025-11-04, oraz Q3 2026 — 4 937 mln EUR, opublikowane 2026-11-03.
  Przy filtrze dostępności na 2026-10-31 widoczny był tylko Q3 2025;
  po zmianie daty na 2026-11-03 widoczne były oba okresy. Ponowny podgląd
  tego samego pakietu wykazał 0 nowych, 0 korekt i 2 powtórzenia.
  Podgląd duplikatów anulowano bez ponownego zapisu. Test potwierdził
  filtrowanie według daty publikacji i wykrywanie identycznych obserwacji.
- **Obsługa formularza:** formularz rewizji jest przewijany. Po zmianie danych należy ponownie wykonać obliczenie; zapis jest dostępny dopiero po poprawnym obliczeniu. Pole notatek inwestora znajduje się poniżej sekcji wyniku i poprzedniej rewizji.
## Źródła prawdy

- `initial_buy_price` i `initial_buy_date` opisują pierwotną decyzję. UI blokuje
  ich edycję, a `Database.update_position()` dodatkowo odrzuca próbę zmiany.
- `isin` jest kluczem dopasowania instrumentu i po zapisaniu nie może się
  zmienić. `ticker` jest prezentacyjny i może zostać zaktualizowany.
- `average_cost` opisuje bieżący koszt posiadania, a `current_price` wyłącznie
  cenę rynkową. Import transakcji nigdy nie ustawia `current_price`.
- `PositionValuation` jest wspólnym źródłem obliczeń ekonomicznych używanych
  przez UI. Zawiera wycenę pozycji oraz zwrot realizowany przy zamknięciu.

## UI i zapis danych

- `PositionTableModel` tworzy jeden buforowany `PositionRow` na pozycję.
  Wyświetlanie, sortowanie i kolory korzystają z tego samego snapshotu, więc
  nie mogą używać różnych definicji zwrotu.
- Brak ceny jest reprezentowany przez `None` i tekst `Brak ceny`/`—`. Nie jest
  zastępowany zerem ani ceną zakupu.
- `ClosePositionDialog` tylko waliduje i zwraca dane użytkownika. Zapis wykonuje
  `MainWindow`, wywołując atomową metodę `Database.close_position()`. Dzięki
  temu dialog nie miesza odpowiedzialności UI i bazy, a sama operacja nadal jest
  atomowa.
- Zapis rewizji i aktualizacja ceny/dat następnej rewizji odbywają się w jednej
  transakcji przez `insert_review_and_update_position()`.
- Ponowne otwarcie wymaga jawnego podania nowej ilości i średniego kosztu.
  Pierwotna cena, data oraz ISIN pozostają bez zmian.

## Import Lightyear

- Dopasowanie odbywa się wyłącznie po ISIN.
- Dokupienie przelicza ważony `average_cost`; sprzedaż częściowa tylko zmniejsza
  ilość. Sprzedaż całej ilości zamyka pozycję atomowo. To świadoma różnica wobec
  sugestii, aby pozostawić pozycję otwartą z `quantity == 0`, ponieważ taki stan
  łamałby przyjęty invariant domenowy.
- Ponowny import identycznej zawartości CSV jest blokowany przez odcisk SHA-256
  surowych bajtów pliku przechowywany w `lightyear_imports`. Odcisk i zmiany
  pozycji zapisują się w jednej transakcji SQLite; nazwa pliku nie określa
  duplikatu. `init_db()` dodaje tę tabelę przez `CREATE TABLE IF NOT EXISTS`,
  bez przebudowy tabel pozycji. To rejestr importowanych plików, a nie ledger
  transakcji.
- Zmieniona zawartość jest traktowana jako nowy plik, nawet przy tej samej
  nazwie. Aplikacja nie rozpoznaje nakładających się operacji w dwóch różnych
  eksportach, więc nowy plik zawierający również wcześniej importowane wiersze
  może ponownie zmienić ilości i koszt.
- Importy wykonane przed dodaniem rejestru nie mają zapisanych odcisków. Aplikacja
  nie potrafi ustalić, czy ich ponowne zaimportowanie jest bezpieczne; pierwszy
  import historycznego pliku po aktualizacji nadal może powtórzyć jego operacje.
- Import zachowuje dotychczasową obsługę błędów wierszy: poprawne wiersze są
  zapisywane, a błędne zgłaszane w podsumowaniu. Odcisk zapisuje się także dla
  takiego pliku, aby ponowny import jego identycznej zawartości nie powtórzył
  poprawnych wierszy. Poprawione lub zmienione pliki nie są porównywane
  transakcyjnie z wcześniejszymi eksportami.
- `Dividend`, `Conversion`, `Deposit`, wypłaty i odsetki są pomijane.
- Model używa całkowitego `quantity`, dlatego importer jawnie odrzuca ułamkowe
  ilości zamiast je zaokrąglać i po cichu zmieniać dane.

## Świadome ograniczenia

- Projekt nie ma ledgeru transakcji. Ochrona dotyczy wyłącznie identycznych
  plików, nie identycznych operacji przeniesionych do innego eksportu.
- Przy częściowej sprzedaży nie zapisujemy oddzielnego zrealizowanego wyniku;
  `realized_gain` dotyczy pełnego zamknięcia pozycji.
- Pozycje bez ceny rynkowej są pomijane w wartości portfela i w mianowniku
  faktycznej alokacji. UI pokazuje ich brak ceny jawnie.
