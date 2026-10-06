"""Read compatibility with persisted identifiers from the previous release.

These identifiers are deliberately retained: changing them would disconnect
existing Discord buttons and SQLite data. New resources use the current brand.
"""
from pathlib import Path

BRAND = 'imbirxhc'
LEGACY_NAMESPACE = 'boxpvpb'


def compatible_markers(marker):
    return (marker, marker.replace(BRAND, LEGACY_NAMESPACE, 1))


def database_path(data: Path):
    current = data / f'{BRAND}.sqlite3'
    legacy = data / f'{LEGACY_NAMESPACE}.sqlite3'
    if current.exists() and legacy.exists():
        raise ValueError('Znaleziono dwie bazy danych. Wybierz właściwy katalog DATA_DIR; nie łącz baz automatycznie.')
    return legacy if legacy.exists() else current
