# Dziennik Inwestora Value — instrukcja użytkownika

## 1. Do czego służy aplikacja?

Dziennik Inwestora Value pomaga prowadzić portfel inwestycyjny, dokumentować decyzje i okresowo oceniać posiadane spółki.

Aplikacja rozdziela trzy obszary:

- **Pozycja inwestycyjna** — informacje o posiadanych akcjach, cenie zakupu, ilości i aktualnej wycenie.
- **Rewizja inwestycyjna** — rzeczywista ocena inwestora wykonana w określonym dniu.
- **Historia fundamentalna** — dane finansowe spółki i instrumentu z różnych okresów, wraz ze źródłami i datami ich udostępnienia.

Aplikacja jest lokalnym dziennikiem inwestora. Nie jest terminalem giełdowym, nie prowadzi pełnego rejestru transakcji i nie pobiera automatycznie notowań ani wskaźników fundamentalnych.

## 2. Pierwsze uruchomienie

Aplikacja automatycznie tworzy lokalną bazę SQLite:

`data/dziennik.db`

Nowa baza jest pusta. Nie zawiera przykładowych pozycji.

Pracę można rozpocząć przez ręczne dodanie pozycji przyciskiem **+ Dodaj** albo przez import CSV z Lightyear.

Po dodaniu pozycji warto uzupełnić jej aktualną cenę rynkową.

## 3. Pozycje inwestycyjne

Pozycja opisuje posiadany instrument.

W zależności od formularza można uzupełnić między innymi:

- ticker, ISIN i nazwę spółki;
- walutę;
- cenę i datę pierwotnego zakupu;
- ilość akcji oraz średni koszt posiadania;
- tezę inwestycyjną;
- progi decyzyjne;
- aktualną cenę rynkową.

ISIN identyfikuje instrument. Ticker pełni przede wszystkim funkcję prezentacyjną.

Cena pierwotnego zakupu i data zakupu opisują pierwotną decyzję inwestycyjną. Średni koszt posiadania może zmieniać się po dokupieniu akcji.

Aktualną cenę rynkową uzupełnia użytkownik. Brak ceny nie jest zastępowany ceną zakupu ani zerem.

## 4. Rewizje inwestycyjne

Rewizja to zapis rzeczywistej oceny inwestora. Nie jest automatycznie tworzona przy imporcie danych fundamentalnych.

### 4.1. Rozpoczęcie rewizji

Wybierz pozycję i otwórz formularz **Rewizja**.

Uzupełnij:

- **Spółka** — pozycja, której dotyczy analiza.
- **Aktualna cena** — cena rynkowa właściwa dla daty wykonywanej analizy.
- **Data rzeczywistej analizy** — dzień, w którym faktycznie dokonujesz oceny.

Data analizy nie jest datą zakupu akcji ani końcem okresu sprawozdawczego.

Domyślnie formularz wskazuje bieżący dzień. Nie należy cofać daty tylko dlatego, że analizowane dane finansowe pochodzą z wcześniejszego okresu.

W przypadku zapisywania rzeczywiście wykonanej wcześniej analizy aplikacja wymaga dodatkowego potwierdzenia. Należy pamiętać, że zwrot nadal korzysta z bieżącego średniego kosztu pozycji. Aplikacja nie odtwarza historycznego stanu posiadania.

### 4.2. Wprowadzanie metryk

Formularz zawiera sześć metryk:

- P/E ratio;
- Dividend yield;
- D/E ratio;
- ROE;
- Payout ratio;
- Revenue growth 3Y.

Każda metryka może pozostać pusta.

Domyślnie zaznaczone jest pole **brak**. Aby wpisać wartość, odznacz je i wprowadź liczbę zgodnie z jednostką pokazaną obok pola.

Dane można wprowadzić ręcznie albo pobrać z historii fundamentalnej przyciskiem:

**Historia spółki / import JSON / wybór danych…**

Przy danych wpisywanych ręcznie aplikacja nie zna automatycznie ich źródła ani okresu. Informacje o pochodzeniu należy wtedy umieścić w notatkach.

### 4.3. Dane z Lightyear

Lightyear może być wygodnym źródłem wskaźników takich jak P/E, Dividend Yield, D/E, ROE czy Revenue Growth.

Trzeba jednak odróżniać aktualny zestaw wskaźników od danych historycznych.

Wskaźniki pokazywane w sekcji Advanced mogą opierać się na różnych podstawach, na przykład:

- aktualnej cenie rynkowej;
- wynikach TTM, czyli kroczących ostatnich 12 miesiącach;
- trzyletnim CAGR, czyli średniorocznym tempie wzrostu.

Zrzut Lightyear wykonany dzisiaj dokumentuje odczyt wykonany dzisiaj. Nie oznacza to, że takie same wskaźniki obowiązywały w dniu zakupu akcji.

Przy ręcznej rewizji warto zapisać w notatkach źródło, datę odczytu oraz istotne informacje o metodologii.

Jeżeli potrzebne są dane historyczne, należy korzystać z raportów i pakietów JSON zawierających okres finansowy, datę publikacji i definicję metryki.

### 4.4. Obliczenie wyniku

Po uzupełnieniu ceny i metryk kliknij duży przycisk **Oblicz**.

Aplikacja wyświetli:

- stopę zwrotu;
- kategorię inwestycji;
- automatyczną instrukcję decyzyjną;
- podsumowanie zmian metryk w porównaniu z poprzednią rzeczywistą rewizją.

**Ważne:** automatyczna kategoria i instrukcja wynikają z obliczonego zwrotu oraz progów decyzyjnych pozycji. Nie są automatyczną oceną kondycji fundamentalnej spółki.

Metryki służą do dodatkowej analizy. Brak porównania z poprzednią rewizją nie oznacza, że wskaźnik pozostał bez zmian.

Po każdej zmianie danych należy ponownie kliknąć **Oblicz**. Zapis rewizji jest możliwy dopiero po poprawnym obliczeniu wyniku.

### 4.5. Ocena inwestora i zapis

Niżej w formularzu znajduje się sekcja wcześniejszej rzeczywistej rewizji oraz pole:

**Ocena inwestora i decyzja w tej rewizji**

Wpisz własną ocenę, argumenty, ryzyka, zmiany w tezie inwestycyjnej i podjętą decyzję.

Pole notatek znajduje się niżej w przewijanej zawartości formularza. Przy mniejszym ekranie może wymagać przewinięcia okna.

Po sprawdzeniu wszystkich danych i notatek kliknij **Zapisz rewizję**.

Zapis zawiera rzeczywistą datę analizy, użyte wartości metryk, wynik automatyczny, notatki inwestora oraz kopię wybranych danych źródłowych.

Późniejsze korekty danych fundamentalnych nie zmieniają kopii zachowanej w już zapisanej rewizji.

## 5. Historia danych fundamentalnych

Historia fundamentalna jest niezależna od posiadania akcji. Można przechowywać dane spółki także z okresów sprzed pierwszego zakupu.

Do historii można przejść z głównego okna aplikacji albo z formularza rewizji.

Wybór instrumentu odbywa się po ISIN.

### 5.1. Tabela i szczegóły

Tabela prezentuje między innymi:

- metrykę i zakres danych;
- ISIN, jeśli wartość dotyczy konkretnego instrumentu;
- okres finansowy;
- datę udostępnienia danych;
- datę wyceny;
- wartość i jednostkę;
- definicję wskaźnika;
- źródło;
- zmianę względem wcześniejszego okresu.

Zaznaczenie wiersza pokazuje szczegóły, w tym URL źródła, lokalizację w raporcie, sposób obliczenia i informacje o niepewności.

### 5.2. Filtrowanie historii

Opcja **Tylko informacje dostępne na dzień** ogranicza historię do informacji, które według zapisanych dat były dostępne w wybranym dniu.

Jest to szczególnie ważne przy odtwarzaniu historycznej sytuacji spółki.

Opcja **Pokaż także wcześniejsze wersje korekt** pozwala zobaczyć poprzednie wersje poprawionych danych.

Nie należy utożsamiać okresu finansowego z datą publikacji. Raport za dany rok może być opublikowany dopiero kilka miesięcy po zakończeniu roku.

## 6. Import danych fundamentalnych z JSON

Aplikacja nie pobiera automatycznie raportów ani danych z serwisów finansowych. Pakiet JSON przygotowuje się poza aplikacją, np. z pomocą AI, korzystając z dokumentów źródłowych.

Dokładny format opisano w:

`docs/FUNDAMENTALS_JSON.md`

Przykładowy pakiet znajduje się w:

`examples/fundamentals-v1.json`

Przykład zawiera dane syntetyczne. Nie należy importować go jako rzeczywistych danych jakiejkolwiek spółki.

### 6.1. Przebieg importu

1. Otwórz historię fundamentalną.
2. Wybierz **Importuj JSON…**.
3. Wskaż przygotowany plik JSON.
4. Sprawdź nazwę emitenta, identyfikator, klasy akcji i ISIN.
5. Przejrzyj wszystkie obserwacje, okresy, wartości, definicje oraz źródła.
6. Zwróć uwagę na liczbę nowych rekordów, korekt i powtórzeń.
7. Zaznacz potwierdzenie sprawdzenia danych i zatwierdź import.

Podgląd nie zapisuje danych. Dopiero jawne zatwierdzenie uruchamia zapis.

### 6.2. Powtórzenia i korekty

Identyczne obserwacje są wykrywane i pomijane.

Zmiana danych dla istniejącego klucza obserwacji jest traktowana jako korekta. Nowa wersja zostaje zapisana, a poprzednia pozostaje w historii.

Nie należy usuwać poprzednich wersji tylko dlatego, że opublikowano korektę.

### 6.3. Daty i dostępność danych

Pakiet rozróżnia:

- okres finansowy;
- datę publikacji konkretnej wersji danych;
- datę wyceny, jeżeli jest potrzebna.

Informacje z nieznaną datą publikacji można zachować w historii, ale nie można ich użyć jako potwierdzonego materiału w datowanej rewizji.

Dane opublikowane po dacie analizy również nie mogą być wykorzystane w tej rewizji.

Import nie tworzy rewizji, nie zmienia ilości akcji, ceny rynkowej ani terminu następnej rewizji.

## 7. Wykorzystanie historii w rewizji

W formularzu rewizji kliknij:

**Historia spółki / import JSON / wybór danych…**

Otworzy się historia ograniczona do instrumentu wybranej pozycji.

Domyślnie w trybie wyboru aktywny jest filtr informacji dostępnych na dzień rewizji. Dzięki temu późniejsze dane nie zostaną wykorzystane w starszej analizie.

Dostępne są trzy podstawowe działania:

- **Wybierz najnowsze metryki** — automatycznie zaznacza najnowsze dostępne wartości dla jednoznacznych serii.
- **Zaznacz cały widoczny kontekst** — zaznacza wszystkie widoczne obserwacje, również wcześniejsze okresy.
- **Użyj zaznaczonych danych w rewizji** — przekazuje wybrane obserwacje do formularza.

Można wybrać kilka wierszy za pomocą Ctrl lub Shift.

Jeżeli dla jednej metryki istnieją różne definicje, zakresy lub podstawy okresu, aplikacja może wymagać ręcznego wyboru właściwej serii.

Najnowsza wybrana wartość odpowiedniej metryki wypełnia jej pole w formularzu. Pozostałe wybrane obserwacje pozostają materiałem kontekstowym zachowanym w rewizji.

Przychody mogą być przechowywane i porównywane w historii fundamentalnej, ale nie są jednym z sześciu pól formularza rewizji.

Po zastosowaniu danych wróć do formularza, sprawdź wypełnione pola i kliknij **Oblicz**.

## 8. Odczytanie zapisanej rewizji

Historia rewizji pokazuje wykonane oceny inwestora.

Dwuklik wpisu otwiera szczegóły zapisanej rewizji.

Można tam sprawdzić:

- datę analizy;
- automatyczną kategorię i instrukcję;
- notatki inwestora;
- wartości metryk użyte w formularzu;
- informację, czy dane pochodziły z importu, czy zostały wpisane ręcznie;
- zachowane kopie wybranych obserwacji i ich źródeł.

Dzięki zachowanej kopii późniejsza korekta historii fundamentalnej nie zmienia materiału wykorzystanego przy wcześniejszej decyzji.

## 9. Import CSV z Lightyear

Importer CSV służy do importowania obsługiwanych operacji z wyciągu Lightyear.

Aplikacja blokuje ponowny import pliku o identycznej zawartości na podstawie skrótu SHA-256.

Nie wykrywa jednak automatycznie tych samych transakcji w dwóch różnych eksportach. Zmieniony plik może zawierać wcześniej zaimportowane operacje.

Przed importem kolejnego eksportu należy sprawdzić, czy nie powiela on już zaimportowanych transakcji.

Import CSV nie zastępuje pełnego rejestru transakcji.

## 10. Najważniejsze zasady pracy

1. Data rewizji oznacza rzeczywistą datę dokonania oceny.
2. Okres sprawozdawczy nie jest datą publikacji raportu.
3. Bieżących wskaźników z Lightyear nie należy automatycznie przypisywać do historycznej daty zakupu.
4. Brak danych nie oznacza wartości zero.
5. Automatyczna instrukcja wynika z progów zwrotu, a nie z pełnej analizy fundamentalnej.
6. Import danych nie tworzy rewizji i nie zmienia pozycji.
7. Notatki inwestora powinny dokumentować własną ocenę i decyzję.
8. Zachowuj źródła i definicje metryk, aby kolejne porównania miały sens.

## 11. Dokumentacja uzupełniająca

- [README — opis projektu i uruchomienie](../README.md)
- [Decyzje projektowe](DESIGN_DECISIONS.md)
- [Format JSON dla AI i przykład](FUNDAMENTALS_JSON.md)