# imbirxhc

Bot Discord dla jednego serwera imbirxhc, Python 3.11+. Zawiera powitania z aktualnym licznikiem członków, weryfikację, tickety, transkrypty HTML, propozycje i trwałe głosowania, `/setup`, `/mute` z potwierdzeniem oraz `/degradacja`.

## Twój serwer — konfiguracja gotowa

W `.env` i `.env.example` wpisano podane ID. Token pozostaje pusty. Aplikacja została już przez Ciebie przemianowana w Developer Portal; nie twórz drugiej aplikacji.

| Ustawienie | ID |
| --- | --- |
| Serwer | `1198214879690096690` |
| Support | `1556395248601800865` |
| Gracz | `1556395872399401077` |
| Kary | `1556404308742770820` |
| Propozycje | `1556400982634795048` |
| Panel ticketów | `1556401523398025336` |
| Weryfikacja | `1556410211445514291` |
| Logi ticketów | `1556531672319660122` |
| Powitania `👋・witaj` | `1556399221857460224` |

`STAFF_ROLE_IDS` zachowuje dokładnie tę kolejność od najniższej do najwyższej:

| Ranga | ID |
| --- | --- |
| SUPPORT | `1556395248601800865` |
| JR.MODERATOR | `1556396223659909211` |
| MODERATOR | `1556396475297038467` |
| HEAD MODERATOR | `1556396976881270864` |
| ADMIN | `1556397477983158313` |
| MANAGEMENT | `1556397926849450135` |

Nazwy w tabeli są opisem. Kod rozpoznaje rangi wyłącznie po ID. Degradacja wymaga niższego miejsca w tej liście oraz niższej pozycji na Discordzie. Możesz pominąć kilka rang lub wybrać rolę gracza jako rangę docelową. Sprawdzana jest kolejność obecnej i docelowej rangi; niezgodność innych rang jest logowana, ale nie blokuje poprawnej degradacji. Rola gracza jest niższa od wszystkich rang administracyjnych w konfiguracji i musi być niższa również na Discordzie. Zachowuje role spoza listy i sprawdza najwyższą rolę moderatora, osoby moderowanej oraz bota. Support+ nadal oznacza rolę Support lub dowolną wyższą rolę według hierarchii Discorda.

### Gdzie wkleić token i jak uruchomić

Otwórz plik `.env` **obok `bot.py`** w katalogu projektu `imbirxhc`. Wklej swój token samodzielnie bezpośrednio po `DISCORD_TOKEN=`. Nie wpisuj go do `.env.example`, kodu ani czatu. Na hostingu preferuj sekret `DISCORD_TOKEN` w jego panelu.

Polecenia wykonaj w katalogu zawierającym `bot.py`:

```sh
python -m pip install -r requirements.txt
python check_config.py
python -u bot.py
```

`check_config.py` sprawdza lokalną konfigurację bez logowania i bez wyświetlania tokenu. Nie potwierdza istnienia kanałów/ról ani ich faktycznej hierarchii. Start z pustym tokenem zostaje zatrzymany przed połączeniem z Discordem.

### Powitania

`WELCOME_CHANNEL_ID=1556399221857460224` wskazuje kanał `👋・witaj`. Po dołączeniu członka bot wysyła kartę powitalną z nagłówkiem **Witaj w imbirxhc!**, złotym akcentem ramki Discord Embed, avatarem i nickiem nad liczbą członków.

Licznik jest odczytywany z `Guild.member_count` po zdarzeniu Discorda, a nie zwiększany na podstawie liczby powitań. Obejmuje wszystkie konta na serwerze, także boty. Po wyjściu członka licznik w **najnowszym powitaniu** jest aktualizowany. Starsze wiadomości są historią ze stanem na czas ich ostatniej aktualizacji. W stopce znajduje się czas aktualizacji.

ID najnowszej wiadomości i oczekujące powitania są trwale zapisane w SQLite. Po restarcie/reconnect licznik najnowszej karty jest ponownie porównywany ze stanem Discorda. Przejściowy błąd wysłania lub edycji jest ponawiany w cyklu odzyskiwania; limity Discorda mogą opóźnić aktualizację. Ręcznie usunięte powitanie nie jest odtwarzane w pętli. Bot nie wysyła powitań wszystkim dotychczasowym członkom po uruchomieniu.

Włącz **Server Members Intent** i zapewnij botowi View Channel, Send Messages, Embed Links oraz Read Message History na kanale powitań. `WELCOME_CHANNEL_ID=0` wyłącza funkcję. Zdarzenia z czasu pełnego wyłączenia procesu nie są historycznie odtwarzane przez bota; po powrocie licznik odzwierciedla aktualny stan. [Dokumentacja zdarzeń członków Discord](https://discordpy.readthedocs.io/en/stable/api.html#discord.on_member_join).

### Zgodność po zmianie nazwy

Schemat bazy i ID Discorda nie zostały zmienione. Nowe bazy nazywają się `imbirxhc.sqlite3`, a nowe transkrypty `imbirxhc-IDENTYFIKATOR.html`. Jeżeli w tym samym `DATA_DIR` istnieje baza poprzedniej wersji, bot i `backup.py` użyją jej bez przenoszenia plików WAL. Obecność obu baz powoduje odmowę startu zamiast przypadkowego wybrania pustej bazy.

Moduł `imbirxhc/compat.py` zachowuje jeden dawny identyfikator techniczny: służy do rozpoznawania wcześniej wysłanych przycisków, markerów i starego pliku bazy. Nie jest brandingiem nowych komunikatów. Rejestrowane są cztery nowe widoki oraz cztery ich zgodne warianty dla starych wiadomości. Historyczne transkrypty zachowują zapisane nazwy plików. `/setup` odświeży istniejące główne panele na nowy branding po Twoim uruchomieniu bota; nie połączono się z serwerem w trakcie tych zmian.

Przy aktualizacji wcześniejszego hostingu zatrzymaj starą usługę i zachowaj cały `DATA_DIR`. Nowy katalog projektu zmienia domyślną nazwę projektu Docker Compose, więc sprawdź podłączenie **dotychczasowego wolumenu** przed uruchomieniem. W systemd przenieś dane do nowego `StateDirectory` po zatrzymaniu starej usługi i ustaw właściciela `imbirxhc`, albo dostosuj `DATA_DIR` i `ReadWritePaths` do istniejącego dysku. Nie uruchamiaj dwóch wersji równocześnie.

## Konfiguracja Discorda

1. Wejdź na https://discord.com/developers/applications i otwórz swoją istniejącą aplikację `imbirxhc`. Token wpisujesz samodzielnie w sekretach hostingu albo lokalnym `.env`. Nie publikuj go i nie wpisuj w kodzie.
2. **Bot → Privileged Gateway Intents**: włącz **Server Members Intent** i **Message Content Intent**. Presence Intent nie jest potrzebny.
3. **OAuth2 → URL Generator**: zaznacz `bot` i `applications.commands`. Zaproś bota na właściwy serwer.
4. Uprawnienia bota: View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Manage Messages, Manage Channels, Manage Roles i Moderate Members. Nie wymaga Administratora. Zapewnij te uprawnienia również w nadpisaniach kanałów.
5. Umieść rolę bota ponad rolą gracza oraz wszystkimi rangami, którymi ma zarządzać. Moderator musi mieć najwyższą rolę wyższą niż osoba moderowana. Właściciel serwera nie może być moderowany. Timeout administratora jest odrzucany.
6. Discord → Ustawienia użytkownika → Zaawansowane → **Tryb dewelopera**. Kliknij prawym przyciskiem serwer, rolę lub kanał → **Kopiuj ID**.
7. Przygotuj kanały tekstowe: kary, propozycje, panel ticketów, weryfikacja i opcjonalnie logi ticketów. Bot identyfikuje je po ID; nazwy mogą być dowolne. Kategorie ticketów tworzy sam, gdy są potrzebne.
8. Ustaw konfigurację z tabeli poniżej. `STAFF_ROLE_IDS` ma zawierać wyłącznie rangi administracyjne, bez roli gracza, kosmetycznych i pingów.
9. Uruchom bota, następnie jako właściciel lub Administrator wykonaj `/setup`. Komendy są synchronizowane dla `GUILD_ID` przy starcie procesu. Panele pozostają na serwerze po restarcie.

## Zmienne środowiskowe

| Zmienna | Wartość |
| --- | --- |
| `DISCORD_TOKEN` | Wymagany sekret tokenu bota |
| `GUILD_ID` | ID serwera |
| `SUPPORT_ROLE_ID` | ID roli Support; ta rola i role wyższe dają dostęp do funkcji administracyjnych |
| `PLAYER_ROLE_ID` | ID roli nadawanej przy weryfikacji |
| `PUNISHMENTS_CHANNEL_ID` | ID kanału kar |
| `SUGGESTIONS_CHANNEL_ID` | ID kanału propozycji |
| `TICKET_PANEL_CHANNEL_ID` | ID kanału panelu ticketów |
| `VERIFY_CHANNEL_ID` | ID kanału weryfikacji |
| `TICKET_LOG_CHANNEL_ID` | Opcjonalny ID kanału transkryptów; `0` wyłącza wysyłkę kopii |
| `WELCOME_CHANNEL_ID` | Kanał powitań z licznikiem członków; `0` wyłącza powitania |
| `STAFF_ROLE_IDS` | ID rang administracyjnych od najniższej do najwyższej, oddzielone przecinkami; puste blokuje degradację |
| `DATA_DIR` | Katalog trwałych danych; lokalnie `./data`, na hostingu ścieżka trwałego wolumenu |

Lokalny `.env` jest już przygotowany; uzupełnij tylko token. Po pobraniu ZIP skopiuj `.env.example` do `.env` — ZIP celowo nie zawiera pliku sekretów. Środowisko ma pierwszeństwo przed `.env`. Prawdziwy `.env` jest wykluczony z repozytorium i obrazu Docker.

```sh
python -m venv .venv
# Linux:
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -u bot.py
# Windows:
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -u bot.py
```

## Hosting 24/7

Bot działa na zewnętrznym serwerze jako proces Python bez GUI, przeglądarki i stale włączonego komputera użytkownika. Wybierz usługę dla botów/background workers bez usypiania i z trwałym dyskiem. Nie wymaga portu HTTP. Nie stosuj sztucznego serwera WWW do utrzymywania procesu przy życiu.

### Co przesłać

Prześlij z tego katalogu:

- `bot.py`, cały katalog `imbirxhc/`, `requirements.txt`;
- `README.md`, `.env.example`, `backup.py`, `check_config.py`;
- dla Docker: `Dockerfile`, `compose.yaml`, `.dockerignore`;
- dla VPS z systemd: `deploy/imbirxhc.service`.

`tests/`, `requirements-dev.txt` i `TEST_REPORT.md` są opcjonalne na hostingu. Nie przesyłaj lokalnego środowiska `.venv`, cache ani `.env` zawierającego token, jeśli hosting ma panel sekretów. Przy migracji istniejącego bota przenieś również **cały trwały katalog `DATA_DIR`** po zatrzymaniu starego procesu. Przy pierwszym wdrożeniu baza utworzy się automatycznie.

### Hosting z panelem Python

1. Wybierz Python 3.11 lub 3.12 i katalog roboczy zawierający `bot.py`.
2. Instalacja: `python -m pip install -r requirements.txt`.
3. W panelu sekretów/zmiennych ustaw wszystkie wymagane pola z tabeli. `DISCORD_TOKEN` przechowuj jako sekret.
4. Podłącz trwały dysk, np. `/app/data`, i ustaw `DATA_DIR=/app/data`. Użytkownik procesu musi mieć prawo zapisu. Używaj lokalnego dysku hostingu obsługującego blokady plików SQLite, nie współdzielonego NFS.
5. **Komenda startowa: `python -u bot.py`**.
6. Włącz **Always on / Background worker** oraz **Restart on crash / Automatic restart**. Ustaw odstęp restartów ok. 15 sekund i limit zatrzymania co najmniej 60 sekund (dłuższy przy dużych transkryptach). Udostępnij procesowi SIGTERM przy zatrzymaniu.
7. Ustaw dokładnie **jedną instancję/replikę**, wyłącz autoscaling i nakładające się wdrożenia. Zatrzymaj poprzednią wersję przed uruchomieniem nowej. Blokada `process.lock` odrzuca drugą instancję korzystającą z tego samego katalogu danych.
8. Sprawdź log `GOTOWY` i wykonaj `/setup` tylko przy pierwszej konfiguracji lub w celu naprawy paneli. Nie dodawaj `/setup` do skryptu startowego.

**UWAGA: efemeryczny system plików może skasować SQLite i transkrypty przy redeployu, restarcie kontenera lub migracji hosta. Bez trwałego dysku restart nie gwarantuje zachowania danych.** Dane to `DATA_DIR/imbirxhc.sqlite3`, pliki WAL/SHM podczas pracy oraz `DATA_DIR/transcripts/`. Nigdy nie kieruj `DATA_DIR` do katalogu tymczasowego ani katalogu nadpisywanego wdrożeniem.

### Docker Compose

Ustaw zmienne w środowisku serwera lub w mechanizmie sekretów dostawcy. Wariant Compose pobiera je ze środowiska procesu wywołującego Compose. Następnie:

```sh
docker compose up -d --build
docker compose logs -f --tail=100 imbirxhc
```

`restart: unless-stopped` zapewnia restart po awarii i starcie usługi Docker. Nazwany wolumen `bot-data` przechowuje bazę oraz transkrypty. **Nie wykonuj `docker compose down -v`**, ponieważ usuwa wolumen. Zachowaj stałą nazwę projektu Compose podczas redeployów, żeby korzystać z tego samego wolumenu. Standardowe `docker compose down` zatrzymuje usługę celowo; uruchom ją ponownie przez `up -d`. Logi mają rotację (3 × 10 MB). Upewnij się, że Docker startuje wraz z systemem.

### VPS Linux z systemd

Administrator VPS powinien utworzyć użytkownika systemowego `imbirxhc`, umieścić projekt w `/opt/imbirxhc`, utworzyć tam `.venv` i zainstalować zależności. Plik `/etc/imbirxhc.env` powinien zawierać konfigurację w formacie `NAZWA=wartość`, być własnością roota i mieć uprawnienia `600`. W tym wariancie token trafia do zabezpieczonego pliku środowiskowego na VPS, nie do projektu.

Skopiuj dostarczony plik jednostki do `/etc/systemd/system/imbirxhc.service`, potem:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now imbirxhc
sudo journalctl -u imbirxhc -f
```

Systemd tworzy `/var/lib/imbirxhc`, używa go jako `DATA_DIR`, uruchamia bota przy starcie maszyny i ponawia po awarii co 15 s. `sudo systemctl stop imbirxhc` wykonuje celowe zatrzymanie, a `sudo systemctl restart imbirxhc` restart. Ten wariant nie wymaga Dockera. Używaj jednego nadzorcy procesu.

### Reconnect, restart i utrzymanie

- `bot.start(..., reconnect=True)` obsługuje przejściowe rozłączenia Discorda. `on_disconnect` i `on_resumed` logują stan; `on_ready` może wykonać się wielokrotnie i wyłącznie loguje gotowość.
- `setup_hook` otwiera bazę, rejestruje cztery persistent views oraz ich cztery warianty zgodności (`timeout=None`, stałe `custom_id`) i synchronizuje komendy. Widoki odczytują stan konkretnej wiadomości lub kanału z SQLite. Liczniki są odtwarzane z głosów po starcie.
- `/setup` sprawdza zapisane ID wiadomości. Gdy ID nie zostało zapisane przed awarią, szuka własnej wiadomości z unikalnym markerem. Nie tworzy nowej wiadomości w reakcji na brak uprawnień lub przejściowy błąd HTTP.
- Tworzenie ticketów ma trwały stan `creating`, a zamykanie `closing`. Zadanie odzyskiwania wznawia przerwane operacje. Kanał ma znacznik UUID w temacie, kategoria ID w bazie. Zarezerwowane nazwy kategorii `imbirxhc-SERVER_ID-TYP` służą wyłącznie odzyskaniu przerwy między utworzeniem kategorii a zapisem ID. Nie twórz ręcznie takich kategorii ani nie zmieniaj znaczników.
- Zamknięcie następuje najwcześniej po 3 sekundach; kolejka, historia i limity Discorda mogą wydłużyć ten czas. Przed usunięciem kanału powstaje lokalny transcript; jeśli skonfigurowany kanał logów nie przyjmie pliku, zamknięcie czeka i jest ponawiane. Napraw uprawnienia lub limit pliku. Brak DM nie blokuje zamknięcia.
- Głosy i inne mutacje są serializowane; głosowanie ma klucz `(propozycja, użytkownik)` i transakcje SQLite. WAL, `synchronous=FULL`, busy timeout oraz zapytania parametryzowane chronią spójność danych.
- SIGTERM/SIGINT zatrzymują zadanie odzyskiwania, połączenie Discorda i bazę. Operacje w toku mają czas na zakończenie; po twardej awarii odzyskiwanie korzysta z zapisanego stanu. Błędy krytyczne kończą proces niezerowym kodem dla nadzorcy.
- Nieprawidłowy token lub wyłączone wymagane intents trzeba naprawić w konfiguracji. Automatyczny restart nie naprawi takich błędów.
- Monitoruj logi, wolne miejsce, zużycie pamięci i dostępność procesu. Nie ma gwarancji dostępności samego hostingu/Discorda. Długotrwały brak miejsca na dysku wymaga interwencji.

### Kopie i odtwarzanie

Do spójnej kopii działającej bazy użyj `python backup.py /sciezka-kopii/imbirxhc.sqlite3`. Skrypt używa SQLite Backup API; samo kopiowanie głównego pliku podczas pracy może pominąć WAL. Przechowuj kopie poza tym samym hostem i regularnie sprawdzaj ich odtworzenie. Transkrypty kopiuj osobno; dla wspólnego punktu w czasie zatrzymaj bota i skopiuj cały `DATA_DIR`.

Odtwarzanie: zatrzymaj proces, zachowaj poprzedni katalog jako kopię, odtwórz bazę i transkrypty do pustego trwałego katalogu, ustaw `DATA_DIR` i uprawnienia, uruchom jedną instancję. Nie mieszaj plików WAL starej bazy z nową kopią. Utrata bazy nie pozwala odzyskać kompletu głosów z samych wiadomości Discorda.

## Zachowanie i ograniczenia

- Ticket może zająć i zamknąć wyłącznie Support+; autor otwiera ticket i opisuje sprawę. Jedna aktywna sprawa danego typu na autora. Prywatność kanału obejmuje autora i Support+, a administratorzy Discorda zawsze mają dostęp z racji Administratora.
- W trakcie zamykania blokowane jest pisanie w nadpisaniach kanału. Administratorzy mogą ominąć tę blokadę — nie dopisuj wiadomości podczas eksportu historii.
- Propozycja jest najpierw zapisywana i publikowana, dopiero później usuwana jest oryginalna wiadomość, aby awaria nie utraciła jej treści. Bardzo długi tekst ma kopię TXT. Linki do załączników są zachowywane; Discord może wygasić URL. Bot nie archiwizuje binarnych załączników.
- Potwierdzenia `/mute` i prywatne menu wyboru mają limit 120 s. Po restarcie otwórz menu ponownie przez trwały przycisk. Potwierdzenie kary nie jest automatycznie wznawiane.
- Degradacja zmienia zestaw ról jednym żądaniem Discorda i zachowuje role spoza `STAFF_ROLE_IDS`. Nie koordynuje zmian wykonywanych równocześnie przez inne boty. Awaria dokładnie po wykonaniu operacji Discorda, a przed zapisem jej sukcesu może zostawić audyt `pending`; sprawdź wtedy faktyczne role ręcznie. Bot nie ponawia kary w ciemno.
- Discord i SQLite nie tworzą wspólnej transakcji. Markery ograniczają duplikaty paneli/kanałów po awarii, lecz DM z transkryptem może być ponowiony po awarii przed zapisem potwierdzenia wysyłki.
- Nie usuwaj ręcznie aktywnych kanałów ani bazy. Jeśli kanał został zewnętrznie usunięty podczas zamykania, bot zapisze stan zamknięty i błąd braku historii; utraconych wiadomości nie odtworzy.
- Biblioteka `discord.py` na Pythonie 3.11 wypisuje ostrzeżenie o wycofywanym `audioop`. Bot nie używa głosu; ostrzeżenie nie blokuje działania.

## Testy lokalne

```sh
python -m pip install -r requirements-dev.txt
python -m compileall -q bot.py imbirxhc tests backup.py check_config.py
python -m pytest -q
```

Wyniki i rozróżnienie testów lokalnych od Discorda znajdują się w `TEST_REPORT.md`. Rejestracja trwałych widoków i reconnect są oparte na oficjalnej dokumentacji: https://discordpy.readthedocs.io/en/stable/api.html oraz https://github.com/Rapptz/discord.py/blob/master/examples/views/persistent.py.

## Test na prawdziwym Discordzie — do wykonania po konfiguracji

1. Uruchom bota, sprawdź logi gotowości, wykonaj `/setup` dwa razy: ma zostać jeden panel ticketów i jeden weryfikacji.
2. Zweryfikuj konto gracza, kliknij ponownie: rola pozostaje, pojawia się informacja o wcześniejszej weryfikacji.
3. Otwórz ticket każdego typu. Drugi tego samego typu powinien zostać odrzucony. Sprawdź widoczność zwykłym kontem gracza oraz Support+. Dwie osoby Support klikają zajęcie — tylko jedna wygrywa.
4. Dodaj propozycję z tekstem i obrazkiem; sprawdź usunięcie oryginału. Kliknij ZA dwa razy, potem ZA i PRZECIW; sprawdź usuwanie i przenoszenie głosu. Zagłosuj równocześnie z dwóch kont.
5. Zostaw ticket zajęty i propozycję z głosami. Zrestartuj proces. Sprawdź starą weryfikację, stary panel ticketów, przyciski starego ticketa i głosowanie starej propozycji. Autor, osoba obsługująca i liczniki mają pozostać.
6. W środowisku testowym przerwij sieć procesu i przywróć. Sprawdź logi rozłączenia/wznowienia, ewentualne powtórne `on_ready`, działanie starych przycisków oraz brak nowych paneli, kategorii i kanałów. **Dopiero rzeczywiste wykonanie zalicza test reconnectu.**
7. Zamknij ticket; sprawdź transcript HTML na dysku, DM i kanał logów. Powtórz z zablokowanymi DM. Ostatni ticket ma usunąć pustą kategorię. Sprawdź restart podczas trzysekundowego oczekiwania i podczas tworzenia ticketa.
8. `/mute`: anuluj, potem potwierdź na koncie testowym. Sprawdź limit 28 dni i odmowę dla równych/wyższych ról. `/degradacja`: sprawdź niższą rangę, zachowanie kosmetycznych ról i log kary.
9. Zatrzymaj proces SIGTERM, uruchom ponownie. W środowisku testowym zabij proces awaryjnie i sprawdź automatyczny restart nadzorcy.
10. Wykonaj redeploy z tym samym wolumenem i odtwórz kopię bazy w środowisku testowym. Zweryfikuj zachowanie danych. Kontroluj logi i zasoby przez kilka dni.
11. Wejdź kontem testowym: na kanale `1556399221857460224` sprawdź powitanie, nick, avatar i liczbę wszystkich członków. Wyjdź dwoma kontami, a potem wejdź kolejnym; licznik ma odzwierciedlać każdą zmianę. Zrestartuj bota i ponownie sprawdź aktualizację ostatniej karty bez dodatkowego powitania.

## Formularze ticketów

Po wybraniu typu otwiera się formularz Discord. Kanał powstaje dopiero po wysłaniu poprawnie wypełnionego formularza. Wszystkie pola są wymagane.

- Zgłoś gracza: nick osoby zgłaszającej, nick zgłaszanego gracza i opis sytuacji.
- Backup: opis całej sytuacji.
- Unban: nick osoby nakładającej bana, własny nick w grze i powód otrzymania bana.
- Inna sprawa: opis sytuacji.

Odpowiedzi są zapisane w SQLite i widoczne w głównym embedzie ticketa nad przyciskami Zajmij ticket / Zamknij ticket. Pozostają dostępne po restarcie i w transkrypcie. Formularz wygasa po 10 minutach; otwórz wtedy nowy z panelu. Dawne tickety pozostają dostępne, ale nie mają automatycznie dopisanych odpowiedzi.
