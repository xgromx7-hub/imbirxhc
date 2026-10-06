# Zmiany struktury pod Railway

Utworzono nowy folder do publikacji. Istniejąca lokalna instalacja, token, baza i proces bota nie zostały zmienione.

- `bot.py`, `requirements.txt` i inne pliki projektu znajdują się bezpośrednio w ROOT paczki. ZIP ma ten sam płaski układ, bez nadrzędnego katalogu.
- Zachowano pojedynczy pakiet Python `imbirxhc/`; jego kod, entrypoint i zależności są identyczne bajt po bajcie z dotychczasową wersją.
- Dodano `railway.json`: Railpack, start `python -u bot.py`, restart ALWAYS, brak healthcheck HTTP i cron, zerowy overlap, 60 sekund na SIGTERM.
- Dodano `.python-version` z Python 3.11.
- `.env.example`: zachowano pusty token, ID i hierarchię; zmieniono wyłącznie domyślną ścieżkę danych na `/app/data`.
- `.gitignore` i `.dockerignore`: rozszerzono wykluczenia sekretów, baz i plików pomocniczych SQLite.
- Opcjonalny `Dockerfile` przeniesiono do `deploy/Dockerfile`; `compose.yaml` wskazuje tę lokalizację. Nie przechwytuje on teraz automatycznego wykrywania aplikacji Python w ROOT Railway.
- README opisuje wgrywanie do ROOT, stare pliki do usunięcia, ustawienia Railway, wszystkie zmienne i migrację danych na Volume. Instrukcję funkcji bota zachowano w `docs/BOT_GUIDE.md`, poprzednie raporty w `docs/history/`.
- Test konfiguracji nie wymaga już prywatnego `.env`; dodano testy struktury, importów, entrypointu i cyklu życia.
- Nie kopiowano `.env`, baz, transkryptów, logów, środowiska Python ani cache do paczki wynikowej.

Nie zmieniono funkcji, schematu SQLite, ID ani kolejności staff. Nie opublikowano zmian na GitHub ani Railway. Wszystkie czynności wdrożeniowe wymagane po stronie użytkownika są w README.
