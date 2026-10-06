# Raport zmian — imbirxhc

Projekt otrzymał nazwę `imbirxhc`, podane ID serwera i sześciu rang oraz powitania na kanale `1556399221857460224`. Lokalny `.env` ma pusty `DISCORD_TOKEN`. Nie uruchamiano połączenia z Discordem. Wynik testów: **91 zaliczonych**; składnia i zależności poprawne.

## Wszystkie zmienione i dodane pliki

Ścieżki poniżej są względem katalogu projektu `imbirxhc`.

| Plik | Zmiana |
| --- | --- |
| `.env` | Nowy lokalny plik: wszystkie ID, uporządkowane rangi, kanał powitań i pusty token. Nie trafia do ZIP. |
| `.env.example` | Te same jawne ID oraz komentarz opisujący kolejność rang; token pusty. |
| `bot.py` | Importy z pakietu `imbirxhc` i nowa nazwa klasy klienta. Mechanizm startu/reconnect/shutdown zachowany. |
| `backup.py` | Nowa nazwa projektu i wybór właściwej bazy również przy aktualizacji poprzedniej wersji. |
| `check_config.py` | Nowa walidacja konfiguracji bez logowania i bez wyświetlania tokenu. |
| `Dockerfile` | Kopiowanie nowego katalogu pakietu. |
| `compose.yaml` | Nazwa usługi `imbirxhc`, dodatkowa zmienna `WELCOME_CHANNEL_ID`; polityka restartu i trwały wolumen zachowane. |
| `deploy/imbirxhc.service` | Nowa nazwa pliku, opis, konto systemowe oraz ścieżki instalacji, środowiska i danych. |
| `imbirxhc/__init__.py` | Przeniesienie wraz z pakietem; zawartość bez zmiany. |
| `imbirxhc/client.py` | Nowe embedy, footery, komunikaty i nazwy transkryptów; zgodność dawnych identyfikatorów; obsługa powitań i kontroli rang. |
| `imbirxhc/config.py` | Rangi jako uporządkowana sekwencja zamiast zbioru, walidacja, kanał powitań, sprawdzanie konfiguracji bez tokenu. |
| `imbirxhc/compat.py` | Nowa warstwa zgodności bazy, przycisków i markerów poprzedniej wersji. |
| `imbirxhc/db.py` | Filtrowanie rekordów po statusie dla ponawiania powitań; schemat tabel bez zmiany. |
| `imbirxhc/rules.py` | Kolejność rang z konfiguracji plus kontrola hierarchii Discorda i możliwości zarządzania rolami. |
| `imbirxhc/views.py` | Nowe identyfikatory przycisków i możliwość rejestracji zgodnych starych wariantów. |
| `imbirxhc/welcome.py` | Nowe trwałe powitania, nick/avatar, licznik, aktualizacja po wyjściu i restarcie, ponawianie błędów oraz deduplikacja. |
| `tests/test_bot.py` | Nowe importy i nazwy, oczekiwania dotyczące kolejności rang, 8 widoków oraz nazw transkryptów. Dotychczasowe scenariusze zachowane. |
| `tests/test_configuration.py` | Nowe testy ID, rang, callbacku degradacji i zgodności po zmianie nazwy. |
| `tests/test_welcome.py` | Nowe testy wejść/wyjść, restartu, ponawiania i licznika. |
| `README.md` | Nowy branding, konfiguracja Twojego serwera, instrukcje tokenu/startu/hostingu, zasady degradacji, powitania i zgodność wcześniejszych danych. |
| `TEST_REPORT.md` | Aktualne wyniki wszystkich testów oraz wskazanie testów niewykonanych na Discordzie. |
| `CHANGE_REPORT.md` | Ten raport. |

Cały katalog projektu i pakiet aplikacji zostały przemianowane. `.gitignore`, `.dockerignore`, `requirements.txt` i `requirements-dev.txt` zachowały treść; nie dodano zależności. Archiwum wynikowe ma nazwę `imbirxhc.zip`. Poprzednia paczka została zachowana poza katalogiem wyników jako kopia robocza.

## Pozostałości poprzedniej nazwy

Pełne przeszukanie tekstowych plików, w tym ukrytych, znalazło jeden wynik w `imbirxhc/compat.py`: dawną przestrzeń identyfikatorów. Jest potrzebna do działania przycisków wysłanych przed zmianą nazwy oraz rozpoznania istniejącej bazy, kategorii i markerów bez duplikowania zasobów. Jej usunięcie mogłoby odciąć stary stan. Nowe komunikaty i identyfikatory używają `imbirxhc`.

Nie zmieniono ID, nazw zmiennych konfiguracyjnych, schematu SQLite ani zasad istniejących ticketów, głosowań, weryfikacji i timeoutów. Degradacja otrzymała wymaganą jawną kolejność rang i dodatkową odmowę przy sprzecznej hierarchii. Historyczne wiadomości na Discordzie nie zostały edytowane, ponieważ nie uruchamiano połączenia; `/setup` odświeży istniejące główne panele po uruchomieniu.

## Powitanie i licznik

Na kanale powitań nowa osoba otrzyma embed „👋 Witaj w imbirxhc!” z tekstem powitania, złotym akcentem, avatarem, nickiem i liczbą członków pod nickiem. Najnowsza karta aktualizuje licznik również przy wyjściu członka; starsze karty pozostają zapisem historycznym. Licznik obejmuje wszystkie konta, łącznie z botami, i nie korzysta z przybliżonej liczby online. Widoczny wynik na rzeczywistym serwerze wymaga testu po wpisaniu tokenu.

## Uruchomienie przez właściciela

Wpisz token wyłącznie po `DISCORD_TOKEN=` w lokalnym `.env` obok `bot.py`, albo w sekretach hostingu. Następnie w katalogu projektu wykonaj `python -m pip install -r requirements.txt`, `python check_config.py` i `python -u bot.py`. Bot wymaga Server Members Intent i Message Content Intent. Dokładne instrukcje oraz lista prób na Discordzie są w README.

## Aktualizacja: degradacja do gracza i formularze

Zmieniono `imbirxhc/rules.py` (gracz jako najniższa ranga docelowa i brak powielania roli), `imbirxhc/client.py` (sprawdzanie rang operacji, trwałe odpowiedzi i panel), `imbirxhc/views.py` (otwieranie formularza przed utworzeniem ticketa), `tests/test_configuration.py` (testy akceptują lokalny skonfigurowany token bez ujawniania go) oraz README i raport testów. Dodano `imbirxhc/ticket_forms.py` i `tests/test_ticket_forms.py`. Liczba zaliczonych testów: 103. Schemat SQLite i istniejące tickety pozostają zgodne.
