# Value Investor Journal — decyzje projektowe po migracji `Position`

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
