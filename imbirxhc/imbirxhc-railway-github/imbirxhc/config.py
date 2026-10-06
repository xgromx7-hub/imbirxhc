import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    token: str
    ids: dict[str, int]
    staff: tuple[int, ...]
    data: Path

    @classmethod
    def load(cls, *, require_token=True):
        load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)
        required = ('GUILD_ID', 'SUPPORT_ROLE_ID', 'PLAYER_ROLE_ID',
                    'PUNISHMENTS_CHANNEL_ID', 'SUGGESTIONS_CHANNEL_ID',
                    'TICKET_PANEL_CHANNEL_ID', 'VERIFY_CHANNEL_ID')
        ids = {key: int(os.environ.get(key, '0')) for key in required}
        ids['TICKET_LOG_CHANNEL_ID'] = int(os.getenv('TICKET_LOG_CHANNEL_ID', '0') or 0)
        ids['WELCOME_CHANNEL_ID'] = int(os.getenv('WELCOME_CHANNEL_ID', '0') or 0)
        if any(ids[k] <= 0 for k in required) or any(v < 0 for v in ids.values()):
            raise ValueError('Ustaw poprawne ID w konfiguracji.')
        if require_token and not os.getenv('DISCORD_TOKEN', '').strip():
            raise ValueError('Uzupełnij DISCORD_TOKEN w lokalnym .env lub sekretach hostingu. Nie połączono z Discordem.')
        ordered = tuple(int(x.strip()) for x in os.getenv('STAFF_ROLE_IDS', '').split(',') if x.strip())
        if len(set(ordered)) != len(ordered) or any(x <= 0 for x in ordered):
            raise ValueError('STAFF_ROLE_IDS wymaga unikalnych dodatnich ID w kolejności od najniższej rangi.')
        if ordered and ordered[0] != ids['SUPPORT_ROLE_ID']:
            raise ValueError('Pierwszą rangą STAFF_ROLE_IDS musi być SUPPORT_ROLE_ID.')
        data = Path(os.getenv('DATA_DIR', 'data')).resolve()
        if require_token:
            data.mkdir(parents=True, exist_ok=True)
        return cls(os.getenv('DISCORD_TOKEN', ''), ids, ordered, data)

