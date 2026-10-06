# Raport testów imbirxhc

Wykonano lokalnie na Windows, Python 3.11.9, discord.py 2.7.1. Ostatni przebieg po konfiguracji serwera, zmianie nazwy i dodaniu powitań: **91 passed, 1 warning**. Wszystkie 28 dotychczasowych testów nadal przechodzą (z dostosowanymi nazwami i oczekiwaną liczbą widoków zgodności). Ostrzeżenie dotyczy `audioop` w bibliotece Discorda, nie jest błędem testu.

## Wyniki

| Scenariusz | Wynik i zakres |
| --- | --- |
| Restart bota | ZALICZONY lokalnie: świeży proces Python odczytał ticket, propozycję i głosy z SQLite; dodatkowo odtworzono nową instancję klienta. Bez logowania do Discorda. |
| Reconnect | WYŁĄCZNIE SYMULACJA zdarzeń `on_disconnect`, `on_resumed`, `on_ready`. Prawdziwy reconnect Discorda **NIEWYKONANY**. |
| Istniejący ticket po restarcie | ZALICZONY lokalnie: odczyt z bazy, zajęcie poprzez callback starego rodzaju przycisku; ponowne zajęcie odrzucone. |
| Istniejąca propozycja po restarcie | ZALICZONY lokalnie: poprzednie głosy zachowane, nowy głos dodany, prawidłowe etykiety liczników. |
| Persistent buttons po restarcie | ZALICZONY lokalnie: `is_persistent`, stabilne i unikalne `custom_id`, rejestracja 4 views i 4 wariantów zgodności w `setup_hook`, callbacki ticketu i propozycji po odtworzeniu klienta. Rzeczywisty dispatch Discord Gateway wymaga testu na serwerze. |
| Powtórne `on_ready` | ZALICZONY lokalnie: nie wywołuje tworzenia paneli i ticketów. |
| Brak duplikatów paneli | ZALICZONY lokalnie: dwa setupy i odzyskanie brakującego ID po symulowanej awarii powodują tylko jedno wysłanie wiadomości. API Discorda zastąpione atrapą. |
| Brak duplikatów kanałów/kategorii | ZALICZONY lokalnie: odzyskanie kanału ze znacznikiem nie wywołuje tworzenia kolejnego kanału/kategorii. |
| Awaryjne zakończenie procesu | ZALICZONY lokalnie: osobny proces zapisuje stan i wykonuje `os._exit(17)` bez zamknięcia SQLite; głosy i ticket są czytelne po awarii. |
| Graceful shutdown | ZALICZONY lokalnie: `close()` czeka na trwającą mutację i zamyka bazę po jej zapisie. Dostarczenie SIGTERM przez docelowy hosting wymaga testu wdrożeniowego. |
| Blokada drugiego procesu | ZALICZONY lokalnie: drugi proces nie uzyskuje blokady; po zwolnieniu blokada może być ponownie uzyskana. |
| Zamykanie po restarcie | ZALICZONY lokalnie: odzyskany stan `closing` zapisuje HTML i metadane przed usunięciem kanału; tekst HTML jest escapowany. |
| Awaria eksportu historii | ZALICZONY lokalnie: błąd historii nie usuwa kanału. |
| Głosowanie współbieżne | ZALICZONY lokalnie: 100 współbieżnych zapisów, usunięcie i zmiana głosu, zachowanie wyników po otwarciu bazy. |
| Parser czasu | ZALICZONY: 6 poprawnych i 6 niepoprawnych przypadków, w tym limit 28 dni. |
| Sanityzacja kanałów | ZALICZONY: znaki specjalne, pusta nazwa po oczyszczeniu i długość. |
| Hierarchia i degradacja | ZALICZONY lokalnie: odmowa wyższej rangi, zachowanie niezwiązanych ról, Support+, ochrona właściciela i równej roli. |

Sprawdzenie składni `compileall` zakończyło się bez błędów. Importy modułów i rejestracja definicji slash commands wykonane w testach. `pip check`: **No broken requirements found**.

## Konfiguracja, branding i powitania — dodatkowe testy

- Porównano każde podane ID z `.env` i `.env.example`, łącznie z kanałem powitań `1556399221857460224`.
- Sprawdzono kolejność sześciu rang, odrzucanie powtórzonych i nieprawidłowych ID oraz blokadę startu z pustym tokenem. `check_config.py` przeszedł bez łączenia z Discordem.
- Przetestowano wszystkie 36 par obecnej i docelowej rangi: wyłącznie niższa ranga jest dozwolona. Sprawdzono rozbieżność z hierarchią serwera oraz brak skonfigurowanej roli.
- Przetestowano zachowanie ról gracza i kosmetycznych, Support+ według hierarchii oraz odmowę zarządzania rolami równymi/wyższymi od bota.
- Wykonano 5 testów callbacku `/degradacja` z atrapą Discorda: sukces i zapis audytu, równy moderator, wyższa osoba moderowana, rola nad botem, brak Manage Roles. Odmowy nie wysyłają operacji zmiany ról.
- Sprawdzono wczytanie poprzedniej bazy, obsługę dawnych przycisków i markerów oraz odmowę startu przy dwóch konkurencyjnych bazach. Schemat SQLite pozostał bez zmian.
- Powitania: wejście z liczbą 100 → wyjście do 99 → wyjście do 98 → nowe wejście do 99, z nickiem nad liczbą członków w embedzie.
- Powitania: deduplikacja tego samego zdarzenia, ponowne wejście tej samej osoby, odświeżenie najnowszej wiadomości po restarcie bez wysyłania dodatkowej.
- Powitania: odzyskanie po przejściowym błędzie wysyłania, pomijanie obcego serwera, brak wymyślonego licznika przy nieznanym stanie Discorda, respektowanie ręcznie usuniętej wiadomości.
- Przeszukano pliki projektu, również pliki ukryte. Jedyny dawny identyfikator występuje w `imbirxhc/compat.py`, jako celowa zgodność zapisanego wcześniej stanu, a nie aktywny branding.

Liczby w testach są symulowanym stanem Gateway. Nie są odczytem z prawdziwego serwera użytkownika.

## Niewykonane

- Logowanie prawdziwym tokenem i rzeczywiste działanie Discord Gateway/REST.
- Prawdziwy reconnect, dispatch starych przycisków przez Discorda, rzeczywiste role/uprawnienia i dostarczenie DM.
- Uruchomienie obrazu Docker, jednostki systemd, restart po awarii na zewnętrznym hostingu oraz redeploy na jego trwałym wolumenie.
- Wielodniowy test ciągłej pracy i obciążenia.

Dostarczono i zapisano ID serwera, ról i kanałów. Token pozostawiono pusty; bota nie uruchomiono na prawdziwym Discordzie. Faktyczna hierarchia, dostęp do kanałów, wygląd powitania w kliencie Discorda i rzeczywisty licznik członków nadal wymagają próby po samodzielnym wpisaniu tokenu. Powyższe scenariusze nie są oznaczone jako zaliczone. Dokładna lista czynności do wykonania jest na końcu README.

## Aktualizacja: degradacja i formularze

Ostatni przebieg: **103 passed, 1 warning**; składnia wszystkich modułów poprawna. Dodatkowo sprawdzono degradację każdej z 6 rang do gracza (bez duplikowania roli gracza), odmowę dowolnej innej roli i ponownej degradacji gracza, wszystkie 4 formularze, wymagane pola, treść embedów oraz trwałość odpowiedzi po restarcie i blokadę powtórnego ticketa. Nie wykonywano rzeczywistych kar ani zgłoszeń na kontach użytkowników.
