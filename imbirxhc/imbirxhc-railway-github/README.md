# imbirxhc — Railway 24/7

Ten katalog jest **ROOT repozytorium**. Wgraj na GitHub jego **zawartość**, łącznie z plikami zaczynającymi się kropką. Nie wgrywaj folderu opakowującego projekt. ZIP również zawiera pliki bez dodatkowego folderu nadrzędnego.

```text
repo/
├── bot.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── .env.example
├── .gitignore
├── .python-version
├── railway.json
├── backup.py
├── check_config.py
├── imbirxhc/
│   ├── __init__.py
│   ├── config.py
│   ├── client.py
│   └── pozostałe moduły .py
├── tests/
├── deploy/
│   ├── Dockerfile
│   └── imbirxhc.service
├── compose.yaml
└── docs/
```

`imbirxhc/` w tym układzie to wyłącznie pakiet Python, potrzebny importom. Nie powinno być `imbirxhc/bot.py`, `imbirxhc/requirements.txt` ani `imbirxhc/imbirxhc/`.

## Naprawa starego repozytorium GitHub

1. Zachowaj dotychczasową wersję w historii Git/na osobnej gałęzi. Nie usuwaj repozytorium ani katalogu `.git` w swoim klonie.
2. Usuń z bieżącej wersji stare repozytoryjne **opakowanie `imbirxhc/`**, jeżeli zawierało cały projekt: `bot.py`, `requirements.txt` i kolejny wewnętrzny folder `imbirxhc/`. Nie nakładaj nowej paczki na pozostawione stare zagnieżdżenie.
3. Usuń stare paczki ZIP, `__pycache__/`, `.pytest_cache/`, środowiska `.venv/venv/`, logi oraz `.env`, jeżeli były w repo. Bazę/transkrypty najpierw zabezpiecz prywatnie, potem wycofaj z repo; nie usuwaj Volume hostingu.
4. Zastąp stare pliki konfiguracyjne wdrożenia plikami z tej paczki. Stary ROOT `Dockerfile`, `Procfile`, `railpack.json`, `nixpacks.toml` lub `railway.toml` nie powinny wymuszać poprzedniej ścieżki ani innego sposobu startu. Jeśli takie pliki dotyczą wyłącznie tego bota, usuń je; innych projektów w repo nie usuwaj. Nie pozostawiaj dwóch konkurencyjnych plików konfiguracji Railway.
5. Wgraj **wszystkie elementy z nowego folderu** bezpośrednio do ROOT. Pojawi się tam nowy folder `imbirxhc/` zawierający już tylko moduły aplikacji.
6. Sprawdź widok GitHub: `bot.py` i `requirements.txt` muszą być widoczne od razu po otwarciu repozytorium, bez wchodzenia w jakikolwiek folder.

Nie oglądano ani nie zmieniano Twojego zdalnego repozytorium. Powyższa lista dotyczy opisanego układu; nie usuwaj innych, niezwiązanych plików. `.gitignore` nie usuwa plików już śledzonych ani sekretów z historii Git.

## Hosting 24/7 — ustawienia Railway

| Ustawienie | Wartość |
| --- | --- |
| Root Directory | **Puste** — usuń poprzednie `/imbirxhc` |
| Config file | Domyślne `/railway.json` z ROOT; usuń stare nadpisanie ścieżki |
| Builder | **Railpack** |
| Build Command | Puste; Railpack zainstaluje `requirements.txt` |
| Start Command | **`python -u bot.py`** |
| Volume Mount Path | **`/app/data`** |
| Zmienna `DATA_DIR` | **`/app/data`** |
| Replicas | **1**, w jednym regionie |
| Serverless / App Sleeping | **Wyłączone** |
| Restart Policy | **Always** (wymaga planu obsługującego tę opcję) |
| Healthcheck Path | Puste; brak serwera HTTP |
| Public domain / public port | Niepotrzebne; nie generuj domeny dla bota |
| Cron / Pre-deploy command | Puste |
| Overlap | 0 sekund |
| SIGTERM → SIGKILL | 60 sekund; w razie dużych transkryptów zwiększ |

`railway.json` ustawia Railpack, start, restart, pusty healthcheck/cron oraz czas zamykania. Zmienne środowiskowe, Volume, wyłączenie Serverless i jedną replikę ustawiasz w panelu Railway. Nie dodano sztucznego serwera WWW ani zmiennej `PORT`. Wybierz plan i limity zasobów umożliwiające stały proces oraz Volume; samo repo nie gwarantuje dostępności hostingu.

Railpack rozpoznaje Python po `bot.py` i `requirements.txt` w ROOT. `.python-version` wybiera linię Python 3.11. Opcjonalny Dockerfile przeniesiono do `deploy/Dockerfile`, aby ROOT Dockerfile nie przejmował automatycznego builda. Usuń również ewentualne stare nadpisanie `RAILWAY_DOCKERFILE_PATH`. Docker Compose nadal może korzystać z tego Dockerfile poza Railway. [Wykrywanie Python w Railpack](https://railpack.com/languages/python/), [konfiguracja Railway](https://docs.railway.com/config-as-code/reference).

## Railway Variables — zachowaj dokładnie

**`DISCORD_TOKEN`: pozostaw istniejącą wartość w Railway.** Nie kopiuj tokenu do repo ani `.env.example`. Paczka nie zawiera `.env`. Nie importuj pustego `DISCORD_TOKEN=` z przykładu na istniejący sekret, bo nadpiszesz go pustą wartością.

Pozostałe zmienne:

```dotenv
GUILD_ID=1198214879690096690
SUPPORT_ROLE_ID=1556395248601800865
PLAYER_ROLE_ID=1556395872399401077
PUNISHMENTS_CHANNEL_ID=1556404308742770820
SUGGESTIONS_CHANNEL_ID=1556400982634795048
TICKET_PANEL_CHANNEL_ID=1556401523398025336
VERIFY_CHANNEL_ID=1556410211445514291
TICKET_LOG_CHANNEL_ID=1556531672319660122
WELCOME_CHANNEL_ID=1556399221857460224
STAFF_ROLE_IDS=1556395248601800865,1556396223659909211,1556396475297038467,1556396976881270864,1556397477983158313,1556397926849450135
DATA_DIR=/app/data
```

Nie zmieniono ID ani kolejności staff. Python jest ustawiony plikiem `.python-version`; jeśli masz `RAILPACK_PYTHON_VERSION`, ustaw `3.11` lub usuń nadpisanie. `PYTHONUNBUFFERED=1` jest opcjonalne, bo polecenie startowe zawiera `-u`.

## SQLite i przenoszenie danych

Podłącz Volume do usługi **przed startem** i ustaw mount `/app/data`. Baza zapisuje się w `DATA_DIR`, zwykle `/app/data/imbirxhc.sqlite3`, a transkrypty w `/app/data/transcripts/`. Wcześniejsza nazwa bazy jest nadal rozpoznawana przez warstwę zgodności.

**Efemeryczny dysk kontenera może utracić bazę po redeployu.** Samo `DATA_DIR=/app/data` nie tworzy trwałego Volume. Volume jest dostępny w czasie uruchomienia, nie builda. [Dokumentacja Railway Volumes](https://docs.railway.com/volumes).

Jeżeli poprzedni bot ma aktywne tickety/głosy, przed przełączeniem zatrzymaj go i przenieś **cały katalog danych** bezpośrednio na Volume, z pominięciem GitHuba. Alternatywnie wykonaj spójną kopię przez `backup.py` i skopiuj transkrypty. Nie kopiuj samej głównej bazy podczas pracy z pominięciem WAL. Nowa paczka celowo nie zawiera danych; uruchomienie na pustym Volume utworzy pustą bazę, nie przeniesie automatycznie wcześniejszych ticketów/głosów.

Jeśli Volume już zawiera właściwe dane, zachowaj go i jego zawartość. Nie kasuj Volume przy przebudowie repo. Nie uruchamiaj jednocześnie lokalnego bota i Railway; blokada plikowa chroni tylko procesy korzystające z tego samego dysku, nie dwie osobne maszyny.

## Zachowane działanie

Kod `bot.py`, cały pakiet aplikacji, skrypt backupu i zależności są identyczne z dotychczasową wersją. Zachowano tickety z formularzami/transkryptami, propozycje/głosy, `/mute`, `/degradacja`, weryfikację, powitania i persistent views.

Proces pozostaje aktywny w `bot.start(..., reconnect=True)`. Obsługuje SIGTERM/SIGINT, zamyka Discorda, zadania i SQLite. Reconnect nie tworzy paneli. Widoki rejestrowane są przy starcie; dane odczytywane są z trwałej bazy. Nie ma GUI ani zależności od przeglądarki. Szczegóły funkcji: [instrukcja bota](docs/BOT_GUIDE.md).

## Sprawdzenie wdrożenia

Po wgraniu zawartości folderu wykonaj redeploy. Oczekiwane logi: wykrycie Python, instalacja zależności, rejestracja persistent views, synchronizacja komend i `GOTOWY`. Następnie sprawdź stare przyciski, głosy i tickety po restarcie. `/setup` wykonuj tylko do utworzenia/odświeżenia paneli; nie jest komendą startową.

Testy lokalne:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q bot.py backup.py check_config.py imbirxhc tests
```

Bez konfiguracji `python -u bot.py` prawidłowo odmawia startu; nie oznacza to błędu struktury repo. Lokalnie ustaw własne zmienne lub prywatny `.env`; do lokalnego dysku użyj `DATA_DIR=./data`. Na Railway używaj wartości z tabeli. Wyniki wykonanych testów: [TEST_REPORT.md](TEST_REPORT.md). Build i wdrożenie na Twoim Railway nie zostały wykonane w tej sesji.
