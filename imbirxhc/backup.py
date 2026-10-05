"""Consistent live SQLite backup. Usage: python backup.py /backup/imbirxhc.sqlite3"""
import os
import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv
from imbirxhc.compat import database_path

load_dotenv(override=False)
source = database_path(Path(os.getenv('DATA_DIR', 'data'))).resolve()
destination = Path(sys.argv[1]).resolve()
if source == destination or not source.exists():
    raise SystemExit('Nieprawidłowa ścieżka źródła lub kopii.')
destination.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
    src.backup(dst)
print('Kopia SQLite gotowa:', destination)
