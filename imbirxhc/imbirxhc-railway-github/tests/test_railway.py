import asyncio
import importlib
import json
import os
import pkgutil
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def test_root_layout_and_railway_configuration():
    assert (ROOT / 'bot.py').is_file()
    assert (ROOT / 'requirements.txt').is_file()
    assert (ROOT / 'imbirxhc/__init__.py').is_file()
    assert not (ROOT / 'imbirxhc/bot.py').exists()
    assert not (ROOT / 'imbirxhc/imbirxhc').exists()
    assert not (ROOT / '.env').exists()
    assert not (ROOT / 'Dockerfile').exists()
    config = json.loads((ROOT / 'railway.json').read_text())
    assert config['build']['builder'] == 'RAILPACK'
    assert config['deploy']['startCommand'] == 'python -u bot.py'
    assert config['deploy']['healthcheckPath'] is None
    assert config['deploy']['restartPolicyType'] == 'ALWAYS'
    assert dotenv_values(ROOT / '.env.example')['DATA_DIR'] == '/app/data'
    assert dotenv_values(ROOT / '.env.example')['DISCORD_TOKEN'] == ''


def test_all_application_imports():
    import imbirxhc
    for module in pkgutil.iter_modules(imbirxhc.__path__):
        importlib.import_module(f'imbirxhc.{module.name}')
    importlib.import_module('bot')
    importlib.import_module('check_config')


def test_exact_entrypoint_without_token(tmp_path):
    env = os.environ.copy()
    env.update({k: v for k, v in dotenv_values(ROOT / '.env.example').items() if v is not None})
    env['DISCORD_TOKEN'] = ''
    env['DATA_DIR'] = str(tmp_path / 'unused-data')
    env['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run([sys.executable, '-u', 'bot.py'], cwd=ROOT, env=env,
                            capture_output=True, encoding='utf-8', timeout=20)
    assert result.returncode != 0
    assert 'Uzupełnij DISCORD_TOKEN' in result.stderr
    assert 'logging in using static token' not in result.stderr
    assert not (tmp_path / 'unused-data').exists()


@pytest.mark.asyncio
async def test_process_waits_then_gracefully_closes_on_stop(monkeypatch):
    import bot as entrypoint
    started, release = asyncio.Event(), asyncio.Event()
    signal_callbacks = {}
    instances = []

    class OfflineBot:
        def __init__(self, config):
            self.closed = False
            instances.append(self)
        async def start(self, token, reconnect):
            assert token == '' and reconnect is True
            started.set()
            await release.wait()
        async def close(self):
            self.closed = True
            release.set()

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, 'add_signal_handler', lambda sig, callback: signal_callbacks.__setitem__(sig, callback))
    monkeypatch.setattr(entrypoint, 'ImbirBot', OfflineBot)
    task = asyncio.create_task(entrypoint.run(type('Settings', (), {'token': ''})()))
    await asyncio.wait_for(started.wait(), 5)
    assert not task.done()
    signal_callbacks[signal.SIGTERM]()
    await asyncio.wait_for(task, 5)
    assert instances[0].closed
