from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from dotenv import dotenv_values

from imbirxhc.compat import BRAND, LEGACY_NAMESPACE, compatible_markers, database_path
from imbirxhc.config import Config
from imbirxhc.client import ImbirBot
from imbirxhc.db import Store
from imbirxhc.rules import demoted_roles, hierarchy, manageable_roles, staff, validate_staff_roles
from imbirxhc.views import Persistent

ROOT = Path(__file__).resolve().parents[1]
RANKS = (1556395248601800865, 1556396223659909211, 1556396475297038467,
         1556396976881270864, 1556397477983158313, 1556397926849450135)
IDS = {
    'GUILD_ID': 1198214879690096690,
    'SUPPORT_ROLE_ID': RANKS[0], 'PLAYER_ROLE_ID': 1556395872399401077,
    'PUNISHMENTS_CHANNEL_ID': 1556404308742770820,
    'SUGGESTIONS_CHANNEL_ID': 1556400982634795048,
    'TICKET_PANEL_CHANNEL_ID': 1556401523398025336,
    'VERIFY_CHANNEL_ID': 1556410211445514291,
    'TICKET_LOG_CHANNEL_ID': 1556531672319660122,
    'WELCOME_CHANNEL_ID': 1556399221857460224,
}


class Role:
    def __init__(self, identifier, position, *, managed=False):
        self.id, self.position, self.managed = identifier, position, managed
    def __ge__(self, other):
        return self.position >= other.position
    def __lt__(self, other):
        return self.position < other.position
    def is_default(self):
        return self.id == 0


@pytest.mark.parametrize('source', ['example', 'environment'])
def test_exact_configuration(source, monkeypatch):
    values = dotenv_values(ROOT / '.env.example')
    assert values['DISCORD_TOKEN'] == ''
    if source == 'environment':
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        configured = Config.load(require_token=False)
        assert configured.ids == IDS and configured.staff == RANKS
    assert {key: int(values[key]) for key in IDS} == IDS
    assert tuple(map(int, values['STAFF_ROLE_IDS'].split(','))) == RANKS


def test_config_preserves_order_and_blocks_empty_token(monkeypatch, tmp_path):
    for key, value in dotenv_values(ROOT / '.env.example').items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    config = Config.load(require_token=False)
    assert config.ids == IDS and config.staff == RANKS
    with pytest.raises(ValueError, match='DISCORD_TOKEN'):
        Config.load()


@pytest.mark.parametrize('bad', [f'{RANKS[0]},{RANKS[0]}', ','.join(map(str, reversed(RANKS))), f'{RANKS[0]},-1'])
def test_invalid_staff_config(monkeypatch, bad):
    for key, value in dotenv_values(ROOT / '.env.example').items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('SUPPORT_ROLE_ID', str(RANKS[0]))
    monkeypatch.setenv('STAFF_ROLE_IDS', bad)
    with pytest.raises(ValueError):
        Config.load(require_token=False)


@pytest.mark.parametrize('current', range(6))
@pytest.mark.parametrize('destination', range(6))
def test_all_six_ranks_and_every_demotion_pair(current, destination):
    roles = [Role(identifier, index + 10) for index, identifier in enumerate(RANKS)]
    cosmetic = Role(999, 1)
    if destination < current:
        result, removed = demoted_roles([cosmetic, roles[current]], roles[destination], RANKS)
        assert result == [cosmetic, roles[destination]]
        assert removed == [roles[current]]
    else:
        with pytest.raises(ValueError):
            demoted_roles([cosmetic, roles[current]], roles[destination], RANKS)


def test_demotion_rejects_discord_order_disagreement():
    roles = [Role(identifier, 100 - index) for index, identifier in enumerate(RANKS)]
    guild = SimpleNamespace(get_role=lambda identifier: next(r for r in roles if r.id == identifier))
    with pytest.raises(ValueError, match='Hierarchia'):
        validate_staff_roles(guild, RANKS)
    with pytest.raises(ValueError):
        demoted_roles([roles[5]], roles[0], RANKS)


def test_staff_role_ids_only_and_missing_role():
    roles = {identifier: Role(identifier, index) for index, identifier in enumerate(RANKS)}
    guild = SimpleNamespace(get_role=lambda identifier: roles.get(identifier))
    assert [r.id for r in validate_staff_roles(guild, RANKS)] == list(RANKS)
    del roles[RANKS[2]]
    with pytest.raises(ValueError, match='Brak'):
        validate_staff_roles(guild, RANKS)


@pytest.mark.parametrize('position', [10, 11])
def test_equal_or_higher_target_blocked(position):
    guild = SimpleNamespace(owner_id=100)
    actor = SimpleNamespace(id=1, top_role=Role(1, 10))
    target = SimpleNamespace(id=2, top_role=Role(2, position), guild=guild)
    bot = SimpleNamespace(id=3, top_role=Role(3, 100))
    with pytest.raises(ValueError):
        hierarchy(actor, target, bot)


@pytest.mark.parametrize('position', [10, 11])
def test_roles_equal_or_above_bot_blocked(position):
    actor = SimpleNamespace(top_role=Role(1, 100))
    bot = SimpleNamespace(top_role=Role(2, 10), guild_permissions=SimpleNamespace(manage_roles=True))
    with pytest.raises(ValueError):
        manageable_roles(actor, bot, [Role(3, position)])


def test_support_plus_and_cosmetic_roles_preserved():
    guild = SimpleNamespace(owner_id=999)
    assert staff(SimpleNamespace(id=1, guild=guild, top_role=Role(3, 50)), Role(RANKS[0], 10))
    assert staff(SimpleNamespace(id=2, guild=guild, top_role=Role(RANKS[0], 10)), Role(RANKS[0], 10))
    assert not staff(SimpleNamespace(id=3, guild=guild, top_role=Role(3, 1)), Role(RANKS[0], 10))
    unrelated = [Role(IDS['PLAYER_ROLE_ID'], 1), Role(88, 2), Role(99, 3)]
    old = [Role(RANKS[0], 10), Role(RANKS[5], 15)]
    new = Role(RANKS[2], 12)
    result, removed = demoted_roles(unrelated + old, new, RANKS)
    assert result == unrelated + [new] and removed == old


@pytest.mark.asyncio
async def test_existing_database_and_buttons_survive_rename(tmp_path):
    path = tmp_path / f'{LEGACY_NAMESPACE}.sqlite3'
    db = Store(path)
    await db.open()
    await db.put('ticket', 'old', {'status': 'open', 'claimed': 77})
    await db.close()
    bot = ImbirBot(Config('', IDS, RANKS, tmp_path))
    try:
        await bot.db.open()
        assert bot.db.path == path
        assert (await bot.db.get('ticket', 'old'))['claimed'] == 77
        bot.action = AsyncMock()
        legacy_view = Persistent(bot, 'inside', namespace=LEGACY_NAMESPACE)
        assert legacy_view.is_persistent()
        await legacy_view.children[0].callback('interaction')
        bot.action.assert_awaited_once_with('claim', 'interaction')
        assert Persistent(bot, 'inside').children[0].custom_id.startswith(BRAND)
    finally:
        await bot.close()


def test_ambiguous_databases_blocked(tmp_path):
    (tmp_path / f'{BRAND}.sqlite3').touch()
    (tmp_path / f'{LEGACY_NAMESPACE}.sqlite3').touch()
    with pytest.raises(ValueError, match='dwie bazy'):
        database_path(tmp_path)


@pytest.mark.asyncio
async def test_old_panel_marker_recognized(tmp_path):
    bot = ImbirBot(Config('', IDS, RANKS, tmp_path))
    bot._connection.user = SimpleNamespace(id=100)
    old = discord.Embed()
    old.set_footer(text=f'previous brand • {LEGACY_NAMESPACE}:panel:ticket')
    message = SimpleNamespace(author=SimpleNamespace(id=100), embeds=[old])
    async def history(**kwargs):
        yield message
    channel = SimpleNamespace(history=history)
    assert await bot.marked_message(channel, 'imbirxhc:panel:ticket') is message
    await bot.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('scenario', ['success', 'equal_moderator', 'above_moderator', 'above_bot', 'no_manage_roles'])
async def test_demotion_command_end_to_end_offline(tmp_path, scenario):
    bot = ImbirBot(Config('', IDS, RANKS, tmp_path))
    await bot.db.open()
    roles = {identifier: Role(identifier, 10 + n) for n, identifier in enumerate(RANKS)}
    me = SimpleNamespace(id=333, top_role=Role(333, 30), guild_permissions=SimpleNamespace(manage_roles=True))
    guild = SimpleNamespace(id=IDS['GUILD_ID'], owner_id=999, get_role=roles.get, me=me)
    actor = SimpleNamespace(id=111, top_role=Role(111, 25), guild=guild)
    target = SimpleNamespace(id=222, top_role=roles[RANKS[4]], guild=guild,
        roles=[Role(0, 0), Role(IDS['PLAYER_ROLE_ID'], 1), Role(444, 2), roles[RANKS[4]]],
        display_avatar=SimpleNamespace(url='https://cdn.discordapp.com/embed/avatars/0.png'), edit=AsyncMock())
    if scenario == 'equal_moderator':
        actor.top_role = target.top_role
    elif scenario == 'above_moderator':
        actor.top_role = roles[RANKS[3]]
    elif scenario == 'above_bot':
        me.top_role = roles[RANKS[3]]
    elif scenario == 'no_manage_roles':
        me.guild_permissions.manage_roles = False
    guild.fetch_member = AsyncMock(side_effect=lambda identifier: actor if identifier == actor.id else target)
    interaction = SimpleNamespace(guild=guild, user=actor,
        response=SimpleNamespace(defer=AsyncMock(), is_done=lambda: True),
        followup=SimpleNamespace(send=AsyncMock()))
    bot.log_demotion = AsyncMock()
    try:
        callback = bot.tree.get_command('degradacja').callback
        if scenario == 'success':
            await callback(interaction, target, roles[RANKS[2]], 'Test lokalny')
            assert [r.id for r in target.edit.call_args.kwargs['roles']] == [IDS['PLAYER_ROLE_ID'], 444, RANKS[2]]
            audit = await bot.db.all('demotion')
            assert len(audit) == 1 and audit[0][1]['status'] == 'applied'
        else:
            with pytest.raises(ValueError):
                await callback(interaction, target, roles[RANKS[2]], 'Test lokalny')
            target.edit.assert_not_called()
            assert not await bot.db.all('demotion')
    finally:
        await bot.close()
