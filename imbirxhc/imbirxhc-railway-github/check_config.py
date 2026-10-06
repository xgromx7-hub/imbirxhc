"""Validate local settings without logging in or displaying the token."""
from imbirxhc.config import Config


def main():
    config = Config.load(require_token=False)
    for name, value in config.ids.items():
        print(f'{name}={value}')
    print('STAFF_ROLE_IDS=' + ','.join(map(str, config.staff)))
    print(f'DATA_DIR={config.data}')
    print('Konfiguracja ID poprawna lokalnie. Istnienie ról/kanałów wymaga sprawdzenia na Discordzie.')
    print('Token nie jest wyświetlany. Ten skrypt nie łączy się z Discordem.')


if __name__ == '__main__':
    main()
