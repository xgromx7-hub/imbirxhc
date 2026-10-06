"""Durable welcome messages and a live count in the latest welcome card."""
import logging

import discord

log = logging.getLogger(__name__)


def member_count(guild):
    # Gateway updates this before dispatching join/remove. Never use an
    # approximate REST count or len(guild.members), which may be a partial cache.
    count = guild.member_count
    if count is None or count < 0:
        raise ValueError('Discord nie udostępnił liczby członków. Sprawdź Server Members Intent.')
    return count


def welcome_embed(record, count):
    e = discord.Embed(
        title='👋 Witaj w imbirxhc!',
        description=(
            'Witaj na naszym serwerze **imbirxhc**!\n'
            'Cieszymy się, że jesteś z nami. Rozgość się i dołącz do gry.\n\n'
            'Zapoznaj się z zasadami i przejdź weryfikację, aby zacząć swoją przygodę.'
        ),
        color=0xD49A45,
        timestamp=discord.utils.utcnow(),
    )
    e.set_author(name='imbirxhc • SPOŁECZNOŚĆ')
    e.set_thumbnail(url=record['avatar'])
    nickname = discord.utils.escape_markdown(record['nickname'])
    e.add_field(name='NOWY CZŁONEK', value=f'**{nickname}**\n<@{record["user"]}>', inline=False)
    e.add_field(name='👥 CZŁONKOWIE SERWERA', value=f'**{count:,}**'.replace(',', ' '), inline=False)
    e.set_footer(text=f'imbirxhc • Stan na czas aktualizacji • {record["marker"]}')
    return e


class Welcome:
    def __init__(self, bot):
        self.bot = bot

    @property
    def enabled(self):
        return bool(self.bot.config.ids.get('WELCOME_CHANNEL_ID'))

    async def join(self, member):
        if not self.enabled:
            return
        joined = (member.joined_at or discord.utils.utcnow()).isoformat()
        key = f'{member.id}:{joined}'
        if await self.bot.db.get('welcome_event', key):
            return
        record = {
            'user': member.id, 'nickname': member.display_name,
            'avatar': member.display_avatar.url, 'joined': joined,
            'channel': self.bot.config.ids['WELCOME_CHANNEL_ID'],
            'marker': f'imbirxhc:welcome:{key}', 'status': 'queued',
        }
        await self.bot.db.put('welcome_event', key, record)
        try:
            await self.publish(member.guild, key, record)
        except (discord.HTTPException, ValueError):
            log.exception('Nie wysłano powitania; zapisano do ponowienia.')
            self.bot.wake.set()

    async def publish(self, guild, key, record):
        count = member_count(guild)
        channel = guild.get_channel(record['channel']) or await self.bot.fetch_channel(record['channel'])
        if not isinstance(channel, discord.TextChannel) or channel.guild.id != guild.id:
            raise ValueError('WELCOME_CHANNEL_ID musi wskazywać kanał tekstowy na skonfigurowanym serwerze.')
        message = None
        if record['status'] == 'sending':
            # Recover the Discord-send / database-commit crash gap without spam.
            message = await self.bot.marked_message(channel, record['marker'], record.get('message'))
        record['status'] = 'sending'
        await self.bot.db.put('welcome_event', key, record)
        if message is None:
            message = await channel.send(embed=welcome_embed(record, count))
        else:
            await message.edit(embed=welcome_embed(record, count))
        latest = {**record, 'message': message.id, 'count': count, 'missing': False}
        await self.bot.db.put('welcome_latest', guild.id, latest)
        record.update(status='done', message=message.id)
        await self.bot.db.put('welcome_event', key, record)
        log.info('Powitanie imbirxhc: użytkownik %s, członkowie %s.', record['user'], count)

    async def refresh(self, guild):
        if not self.enabled:
            return
        latest = await self.bot.db.get('welcome_latest', guild.id)
        if not latest or latest.get('missing'):
            return
        count = member_count(guild)
        if count == latest['count']:
            return
        try:
            channel = guild.get_channel(latest['channel']) or await self.bot.fetch_channel(latest['channel'])
            message = await channel.fetch_message(latest['message'])
            await message.edit(embed=welcome_embed(latest, count))
        except discord.NotFound:
            # Respect manual deletion; do not recreate a welcome on each retry.
            latest['missing'] = True
            await self.bot.db.put('welcome_latest', guild.id, latest)
            log.warning('Usunięto ostatnie powitanie; nowe powstanie przy kolejnym wejściu.')
            return
        except discord.HTTPException:
            log.exception('Nie odświeżono liczby członków; kolejny cykl ponowi aktualizację.')
            return
        latest['count'] = count
        await self.bot.db.put('welcome_latest', guild.id, latest)

    async def recover(self, guild):
        if not self.enabled:
            return
        pending = await self.bot.db.all('welcome_event', statuses=('queued', 'sending'))
        for key, record in sorted(pending, key=lambda item: item[1]['joined']):
            await self.publish(guild, key, record)
