# Testy paczki Railway — 2026-10-06

**107 testów zaliczonych**, 1 ostrzeżenie `audioop` z discord.py na Pythonie 3.11.9. Zależności: `pip check` bez konfliktów. Wszystkie pliki Python przeszły `compileall`; zaimportowano każdy moduł aplikacji, `bot` i `check_config`.

Zachowano dotychczasowe 103 scenariusze testowe. Test konfiguracji prywatnego `.env` przestawiono na publiczny przykład i zmienne środowiskowe, ponieważ paczka GitHub nie może zawierać pliku sekretów. Dodano 4 testy: struktury ROOT/konfiguracji Railway, importów aplikacji, rzeczywistego uruchomienia entrypointu w podprocesie bez tokenu oraz cyklu życia z symulowanym sygnałem zatrzymania.

| Kontrola | Wynik |
| --- | --- |
| `bot.py` i `requirements.txt` bezpośrednio w ROOT | OK |
| Pakiet `imbirxhc/__init__.py` i moduły bez dodatkowego zagnieżdżenia | OK |
| Kod startowy, pakiet, backup i zależności identyczne z poprzednią wersją | OK, porównanie bajt po bajcie 13 plików |
| Wszystkie dotychczasowe systemy, w tym formularze, głosy i trwałe widoki | Dotychczasowe testy lokalne przechodzą |
| Start `python -u bot.py` | Wykonany w podprocesie ze świadomie pustym tokenem i kompletem jawnych ID; właściwy entrypoint odmawia logowania przed inicjalizacją klienta |
| Stały proces i graceful shutdown | Test z atrapą klienta: proces czeka, `reconnect=True`, callback SIGTERM inicjuje zamknięcie |
| Konfiguracja Railway | RAILPACK, właściwy start, ALWAYS, brak HTTP healthcheck/cron, 60 s na zamknięcie |
| `.gitignore` | Sprawdzony przez Git: 9 ścieżek sekretów/danych/cache wykluczonych; 5 ścieżek źródeł i konfiguracji publikowalnych |
| `.env.example` | Pusty token, wszystkie ID zachowane, `DATA_DIR=/app/data` |
| Sekrety | Brak `.env`; skan plików pod kątem formatu tokenów Discord, GitHub i kluczy prywatnych bez trafień |
| Bazy i transkrypty | Nie dołączono do paczki ani ZIP |
| ZIP | Pliki w samym ROOT ZIP; bez folderu opakowującego, sekretów, danych i cache |

**Niewykonane:** build Railpack na Railway, rzeczywisty deploy, test Linux SIGTERM w kontenerze, mount Volume, połączenie Discorda oraz prawdziwy reconnect w tej sesji. Testy lokalne nie zastępują tych prób. Tokenu użytkownika nie odczytywano ani nie modyfikowano; istniejącego procesu nie restartowano.

Raporty z wcześniejszych etapów pozostawiono w `docs/history/` jako historię. Aktualnym wynikiem dla tej paczki jest niniejszy raport.
