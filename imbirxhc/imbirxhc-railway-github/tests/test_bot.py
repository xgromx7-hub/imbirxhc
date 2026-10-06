import asyncio
import subprocess
import sys
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from imbirxhc.config import Config
from imbirxhc.client import ImbirBot, embed
from imbirxhc.db import Store
from imbirxhc.rules import duration, channel_name, demoted_roles, hierarchy, staff
from imbirxhc.views import Persistent


def config(path):
    return Config('test-not-a-token', {k: n for n, k in enumerate(('GUILD_ID', 'SUPPORT_ROLE_ID', 'PLAYER_ROLE_ID', 'PUNISHMENTS_CHANNEL_ID', 'SUGGESTIONS_CHANNEL_ID', 'TICKET_PANEL_CHANNEL_ID', 'VERIFY_CHANNEL_ID', 'TICKET_LOG_CHANNEL_ID'), 1)}, (2,), path)


@pytest.mark.parametrize('value,result', [('30s', 30), ('10m', 600), ('2h', 7200), ('1d', 86400), ('7d', 604800), ('28d', 2419200)])
def test_duration(value, result):
    assert duration(value) == result


@pytest.mark.parametrize('value', ['0s', '-1m', '29d', '1.5h', '4w', 'abc'])
def test_invalid_duration(value):
    with pytest.raises(ValueError):
        duration(value)


def test_channel_name():
    assert channel_name('A B/@!') == 'ticket-a-b'
    assert channel_name('🎮') == 'ticket-gracz'
    assert len(channel_name('x' * 200)) <= 100


class Role:
    def __init__(self, id, position):
        self.id, self.position = id, position
    def __ge__(self, other):
        return self.position >= other.position
    def __lt__(self, other):
        return self.position < other.position


def test_demotion_preserves_unrelated_roles():
    old, new, cosmetic = Role(1, 10), Role(2, 5), Role(3, 1)
    roles, removed = demoted_roles([old, cosmetic], new, (2, 1))
    assert roles == [cosmetic, new] and removed == [old]
    with pytest.raises(ValueError):
        demoted_roles([new], old, (2, 1))


def test_hierarchy_and_support():
    guild = SimpleNamespace(owner_id=99)
    actor = SimpleNamespace(id=1, top_role=Role(1, 5), guild=guild)
    target = SimpleNamespace(id=2, top_role=Role(2, 5), guild=guild)
    bot = SimpleNamespace(id=3, top_role=Role(3, 10))
    assert staff(actor, Role(7, 4))
    assert not staff(actor, Role(7, 6))
    with pytest.raises(ValueError):
        hierarchy(actor, target, bot)
    target.id, target.top_role = 99, Role(2, 1)
    with pytest.raises(ValueError):
        hierarchy(actor, target, bot)


@pytest.mark.asyncio
async def test_votes_concurrency_toggle_and_restart(tmp_path):
    db = Store(tmp_path / 'test.db')
    await db.open()
    await asyncio.gather(*(db.vote('p', n, 1) for n in range(100)))
    assert await db.counts('p') == {1: 100}
    await db.vote('p', 1, 1)
    await db.vote('p', 2, -1)
    assert await db.counts('p') == {1: 98, -1: 1}
    await db.close()
    db = Store(tmp_path / 'test.db')
    await db.open()
    assert await db.counts('p') == {1: 98, -1: 1}
    await db.close()


@pytest.mark.asyncio
async def test_fresh_process_reads_ticket_proposal_votes(tmp_path):
    db = Store(tmp_path / 'test.db')
    await db.open()
    await db.put('ticket', 't', {'status': 'open', 'channel': 123, 'claimed': 99})
    await db.put('proposal', 'p', {'content': 'Treść', 'channel': 44})
    await db.vote('p', 77, 1)
    await db.close()
    script = '''import asyncio,sys
from imbirxhc.db import Store
async def main():
 d=Store(sys.argv[1]); await d.open()
 assert (await d.get('ticket','t'))['claimed']==99
 assert (await d.get('proposal','p'))['content']=='Treść'
 assert await d.counts('p')=={1:1}
 await d.close()
asyncio.run(main())
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path / 'test.db')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_persistent_views_and_repeated_ready(tmp_path):
    bot = ImbirBot(config(tmp_path))
    bot._connection.user = SimpleNamespace(id=100)
    bot.ensure_panel = AsyncMock()
    bot.finish_create = AsyncMock()
    before = []
    for kind in ('ticket', 'verify', 'inside', 'vote'):
        view = Persistent(bot, kind)
        assert view.is_persistent()
        before.extend(item.custom_id for item in view.children)
    await bot.on_ready()
    await bot.on_disconnect()
    await bot.on_resumed()
    await bot.on_ready()
    bot.ensure_panel.assert_not_called()
    bot.finish_create.assert_not_called()
    assert len(before) == len(set(before))
    assert Persistent(bot, 'inside').children[0].custom_id in before
    await bot.close()


@pytest.mark.asyncio
async def test_setup_twice_and_crash_gap_recovery(tmp_path):
    bot = ImbirBot(config(tmp_path))
    bot._connection.user = SimpleNamespace(id=100)
    await bot.db.open()
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 50
    messages = []
    async def history(**kwargs):
        for m in messages:
            yield m
    channel.history = history
    message = SimpleNamespace(id=90, author=SimpleNamespace(id=100), embeds=[], edit=AsyncMock())
    async def send(**kwargs):
        message.embeds = [kwargs['embed']]
        messages.append(message)
        return message
    channel.send = AsyncMock(side_effect=send)
    channel.fetch_message = AsyncMock(return_value=message)
    guild = SimpleNamespace(get_channel=lambda _: channel)
    await bot.ensure_panel(guild, 'ticket')
    await bot.ensure_panel(guild, 'ticket')
    assert channel.send.await_count == 1
    # Simulate missing SQLite message ID after Discord accepted the original send.
    await bot.db.put('panel', 'ticket', {})
    await bot.ensure_panel(guild, 'ticket')
    assert channel.send.await_count == 1
    await bot.close()


@pytest.mark.asyncio
async def test_setup_hook_registers_views_and_restores_dirty(tmp_path):
    bot = ImbirBot(config(tmp_path))
    db = Store(tmp_path / 'imbirxhc.sqlite3')
    await db.open()
    await db.put('proposal', 123, {'dirty': False, 'channel': 44})
    await db.close()
    bot.tree.sync = AsyncMock()
    bot.maintenance = AsyncMock()
    await bot.setup_hook()
    assert len(bot.persistent_views) == 8
    assert (await bot.db.get('proposal', 123))['dirty'] is True
    await bot.close()


@pytest.mark.asyncio
async def test_old_vote_button_dispatch_after_new_bot(tmp_path):
    bot = ImbirBot(config(tmp_path))
    await bot.db.open()
    await bot.db.put('proposal', 123, {'channel': 44, 'dirty': False})
    await bot.db.vote(123, 88, 1)
    await bot.close()
    restarted = ImbirBot(config(tmp_path))
    await restarted.db.open()
    interaction = SimpleNamespace(guild=SimpleNamespace(id=1), user=SimpleNamespace(id=99),
        message=SimpleNamespace(id=123, edit=AsyncMock()),
        response=SimpleNamespace(defer=AsyncMock(), is_done=lambda: True),
        followup=SimpleNamespace(send=AsyncMock()))
    view = Persistent(restarted, 'vote')
    await view.children[0].callback(interaction)
    assert await restarted.db.counts(123) == {1: 2}
    labels = [b.label for b in interaction.message.edit.call_args.kwargs['view'].children]
    assert labels == ['👍 ZA • 2', '👎 PRZECIW • 0']
    await restarted.close()


@pytest.mark.asyncio
async def test_ticket_claim_after_restart(tmp_path):
    bot = ImbirBot(config(tmp_path))
    await bot.db.open()
    await bot.db.put('ticket', 't', {'channel': 50, 'status': 'open', 'claimed': None})
    await bot.close()
    restarted = ImbirBot(config(tmp_path))
    await restarted.db.open()
    guild = SimpleNamespace(id=1, owner_id=99, get_role=lambda _: Role(2, 5))
    user = SimpleNamespace(id=99, guild=guild, top_role=Role(4, 10), mention='<@99>')
    i = SimpleNamespace(guild=guild, user=user, channel_id=50, channel=SimpleNamespace(send=AsyncMock()),
        response=SimpleNamespace(defer=AsyncMock(), is_done=lambda: True), followup=SimpleNamespace(send=AsyncMock()))
    await Persistent(restarted, 'inside').children[0].callback(i)
    assert (await restarted.db.get('ticket', 't'))['claimed'] == 99
    await restarted.action('claim', i)
    assert i.channel.send.await_count == 1
    await restarted.close()


@pytest.mark.asyncio
async def test_crash_committed_wal_survives(tmp_path):
    script = '''import asyncio,os,sys
from imbirxhc.db import Store
async def main():
 d=Store(sys.argv[1]); await d.open()
 await d.put('ticket','crash',{'status':'closing','reason':'Załatwione'})
 await d.vote('p',42,1)
 os._exit(17)
asyncio.run(main())
'''
    path = tmp_path / 'crash.sqlite3'
    result = subprocess.run([sys.executable, '-c', script, str(path)], capture_output=True)
    assert result.returncode == 17
    db = Store(path)
    await db.open()
    assert (await db.get('ticket', 'crash'))['status'] == 'closing'
    assert await db.counts('p') == {1: 1}
    await db.close()


def test_single_process_lock(tmp_path):
    import portalocker
    path = tmp_path / 'process.lock'
    with portalocker.Lock(str(path), timeout=0):
        result = subprocess.run([sys.executable, '-c',
            'import portalocker,sys; portalocker.Lock(sys.argv[1],timeout=0).acquire()', str(path)], capture_output=True)
        assert result.returncode != 0
    with portalocker.Lock(str(path), timeout=0):
        pass


@pytest.mark.asyncio
async def test_graceful_close_waits_for_mutation(tmp_path):
    bot = ImbirBot(config(tmp_path))
    await bot.db.open()
    await bot.operations.acquire()
    closing = asyncio.create_task(bot.close())
    await asyncio.sleep(0.05)
    assert not closing.done()
    await bot.db.put('ticket', 'shutdown', {'status': 'open'})
    bot.operations.release()
    await closing
    db = Store(tmp_path / 'imbirxhc.sqlite3')
    await db.open()
    assert (await db.get('ticket', 'shutdown'))['status'] == 'open'
    await db.close()


@pytest.mark.asyncio
async def test_category_and_channel_recovered_without_creation(tmp_path):
    bot = ImbirBot(config(tmp_path))
    bot._connection.user = SimpleNamespace(id=100)
    await bot.db.open()
    channel = MagicMock(spec=discord.TextChannel)
    channel.id, channel.category_id, channel.topic = 50, 60, 'imbirxhc:ticket:recover'
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = 60
    panel = SimpleNamespace(id=70)
    bot.marked_message = AsyncMock(return_value=panel)
    guild = SimpleNamespace(fetch_channels=AsyncMock(return_value=[channel, category]),
                            create_category=AsyncMock(), create_text_channel=AsyncMock())
    ticket = {'kind': '0', 'author': 88, 'status': 'creating'}
    await bot.finish_create(guild, 'recover', ticket)
    assert ticket['status'] == 'open' and ticket['category'] == 60
    guild.create_category.assert_not_called()
    guild.create_text_channel.assert_not_called()
    channel.send.assert_not_called()
    await bot.close()


@pytest.mark.asyncio
async def test_closing_after_restart_saves_transcript_before_delete(tmp_path):
    bot = ImbirBot(config(tmp_path))
    await bot.db.open()
    ticket = {'status': 'closing', 'channel': 50, 'category': 60, 'kind': '0', 'author': 88,
              'reason': 'Załatwione', 'closed_by': 99, 'close_after': '2020-01-01T00:00:00+00:00'}
    await bot.db.put('ticket', 'closing', ticket)
    await bot.close()
    restarted = ImbirBot(config(tmp_path))
    restarted.config.ids['TICKET_LOG_CHANNEL_ID'] = 0
    await restarted.db.open()
    ticket = await restarted.db.get('ticket', 'closing')
    channel = SimpleNamespace(name='ticket-test', overwrites={}, edit=AsyncMock())
    async def history(**kwargs):
        yield SimpleNamespace(author=SimpleNamespace(id=88), created_at=discord.utils.utcnow(),
            content='<script>alert(1)</script>', embeds=[], attachments=[])
    channel.history = history
    async def delete(**kwargs):
        path = tmp_path / 'transcripts' / 'imbirxhc-closing.html'
        assert path.exists()
        assert '&lt;script&gt;' in path.read_text(encoding='utf-8')
        assert (await restarted.db.get('ticket', 'closing'))['transcript'] == 'imbirxhc-closing.html'
    channel.delete = AsyncMock(side_effect=delete)
    guild = SimpleNamespace(fetch_channel=AsyncMock(return_value=channel), me=SimpleNamespace(id=100))
    restarted.fetch_user = AsyncMock(return_value=SimpleNamespace(send=AsyncMock()))
    restarted.cleanup_category = AsyncMock()
    await restarted.finish_close(guild, 'closing', ticket)
    assert (await restarted.db.get('ticket', 'closing'))['status'] == 'closed'
    channel.delete.assert_awaited_once()
    await restarted.close()


@pytest.mark.asyncio
async def test_failed_history_never_deletes_channel(tmp_path):
    bot = ImbirBot(config(tmp_path))
    await bot.db.open()
    channel = SimpleNamespace(name='ticket-test', overwrites={}, edit=AsyncMock(), delete=AsyncMock())
    async def history(**kwargs):
        raise RuntimeError('Simulated connection failure')
        yield
    channel.history = history
    guild = SimpleNamespace(fetch_channel=AsyncMock(return_value=channel), me=SimpleNamespace(id=100))
    ticket = {'channel': 50, 'author': 88, 'close_after': '2020-01-01T00:00:00+00:00'}
    with pytest.raises(RuntimeError):
        await bot.finish_close(guild, 'failed', ticket)
    channel.delete.assert_not_called()
    await bot.close()
