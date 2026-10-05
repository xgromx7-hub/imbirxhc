from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from imbirxhc.client import ImbirBot
from imbirxhc.config import Config
from imbirxhc.welcome import member_count


def environment(tmp_path):
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 1556399221857460224
    guild = SimpleNamespace(id=1, member_count=100, get_channel=lambda _: channel)
    channel.guild = guild
    message = SimpleNamespace(id=1000, edit=AsyncMock())
    channel.send = AsyncMock(return_value=message)
    channel.fetch_message = AsyncMock(return_value=message)
    config = Config('', {'GUILD_ID': 1, 'WELCOME_CHANNEL_ID': channel.id}, (), tmp_path)
    bot = ImbirBot(config)
    member = SimpleNamespace(id=55, display_name='Nowy Gracz', joined_at=discord.utils.utcnow(),
        display_avatar=SimpleNamespace(url='https://cdn.discordapp.com/embed/avatars/0.png'), guild=guild)
    bot.get_guild = lambda _: guild
    return bot, guild, channel, member, message


@pytest.mark.asyncio
async def test_join_then_two_departures_and_next_join(tmp_path):
    bot, guild, channel, member, message = environment(tmp_path)
    await bot.db.open()
    try:
        await bot.on_member_join(member)
        card = channel.send.call_args.kwargs['embed']
        assert card.title == '👋 Witaj w imbirxhc!'
        assert member.display_name in card.fields[-2].value
        assert card.fields[-1].value == '**100**'
        for count in (99, 98):
            guild.member_count = count
            await bot.on_raw_member_remove(SimpleNamespace(guild_id=1))
            assert message.edit.call_args.kwargs['embed'].fields[-1].value == f'**{count}**'
        guild.member_count = 99
        member.id = 56
        member.display_name = 'Kolejny Gracz'
        await bot.on_member_join(member)
        assert channel.send.await_count == 2
        assert channel.send.call_args.kwargs['embed'].fields[-1].value == '**99**'
        assert 'Kolejny Gracz' in channel.send.call_args.kwargs['embed'].fields[-2].value
    finally:
        await bot.close()


@pytest.mark.asyncio
async def test_repeated_join_dedup_and_rejoin_allowed(tmp_path):
    bot, guild, channel, member, message = environment(tmp_path)
    await bot.db.open()
    try:
        await bot.on_member_join(member)
        await bot.on_member_join(member)
        assert channel.send.await_count == 1
        member.joined_at += timedelta(days=1)
        await bot.on_member_join(member)
        assert channel.send.await_count == 2
    finally:
        await bot.close()


@pytest.mark.asyncio
async def test_restart_updates_latest_without_new_welcome(tmp_path):
    bot, guild, channel, member, message = environment(tmp_path)
    await bot.db.open()
    await bot.on_member_join(member)
    await bot.close()
    restarted, guild, channel, member, message = environment(tmp_path)
    await restarted.db.open()
    try:
        guild.member_count = 97
        await restarted.welcome.recover(guild)
        await restarted.welcome.refresh(guild)
        channel.send.assert_not_called()
        assert message.edit.call_args.kwargs['embed'].fields[-1].value == '**97**'
        await restarted.welcome.refresh(guild)
        assert message.edit.await_count == 1
    finally:
        await restarted.close()


@pytest.mark.asyncio
async def test_transient_send_failure_recovers_without_duplicate(tmp_path):
    bot, guild, channel, member, message = environment(tmp_path)
    await bot.db.open()
    try:
        channel.send.side_effect = discord.HTTPException(SimpleNamespace(status=503, reason='Unavailable'), 'test')
        await bot.on_member_join(member)
        pending = await bot.db.all('welcome_event', statuses=('sending',))
        assert len(pending) == 1
        # Discord accepted the original message despite the response failing.
        bot.marked_message = AsyncMock(return_value=message)
        await bot.welcome.recover(guild)
        assert channel.send.await_count == 1
        assert not await bot.db.all('welcome_event', statuses=('queued', 'sending'))
        assert (await bot.db.get('welcome_latest', guild.id))['message'] == message.id
    finally:
        await bot.close()


@pytest.mark.asyncio
async def test_foreign_guild_ignored_and_missing_count_not_invented(tmp_path):
    bot, guild, channel, member, message = environment(tmp_path)
    await bot.db.open()
    try:
        guild.id = 2
        await bot.on_member_join(member)
        channel.send.assert_not_called()
        guild.member_count = None
        with pytest.raises(ValueError):
            member_count(guild)
    finally:
        await bot.close()


@pytest.mark.asyncio
async def test_deleted_welcome_not_recreated(tmp_path):
    bot, guild, channel, member, message = environment(tmp_path)
    await bot.db.open()
    try:
        await bot.on_member_join(member)
        channel.fetch_message.side_effect = discord.NotFound(SimpleNamespace(status=404, reason='Not found'), 'test')
        guild.member_count = 99
        await bot.welcome.refresh(guild)
        await bot.welcome.refresh(guild)
        assert channel.send.await_count == 1
        assert channel.fetch_message.await_count == 1
    finally:
        await bot.close()
