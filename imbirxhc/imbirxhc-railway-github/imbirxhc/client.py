import asyncio
import html
import io
import logging
import uuid
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from .db import Store
from .compat import LEGACY_NAMESPACE, compatible_markers, database_path
from .rules import channel_name, duration, staff, hierarchy, demoted_roles, validate_staff_roles, manageable_roles
from .views import Persistent, Choice, Confirm, reply
from .welcome import Welcome
from .ticket_forms import validate_answers, add_answers

log = logging.getLogger(__name__)


def now():
    return discord.utils.utcnow().isoformat()


def embed(title, description='', marker=None):
    e = discord.Embed(title=title, description=description, color=0x2B2D31, timestamp=discord.utils.utcnow())
    e.set_footer(text='imbirxhc • SYSTEM ADMINISTRACYJNY' + (f' • {marker}' if marker else ''))
    return e


class ImbirBot(commands.Bot):
    types = {'0': '🚨 Zgłoś gracza', '1': '💬 Inna sprawa', '2': '💾 Backup', '3': '🔓 Unban'}

    def __init__(self, config):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents,
                         allowed_mentions=discord.AllowedMentions.none())
        self.config = config
        self.db = Store(database_path(config.data))
        self.welcome = Welcome(self)
        self.operations = asyncio.Lock()
        self.worker = None
        self.wake = asyncio.Event()
        self.stopping = False
        self.register_commands()

    async def setup_hook(self):
        await self.db.open()
        for key, record in await self.db.all('proposal'):
            record['dirty'] = True
            await self.db.put('proposal', key, record)
        for kind in ('ticket', 'verify', 'inside', 'vote'):
            self.add_view(Persistent(self, kind))
            self.add_view(Persistent(self, kind, namespace=LEGACY_NAMESPACE))
        guild = discord.Object(id=self.config.ids['GUILD_ID'])
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.worker = asyncio.create_task(self.maintenance(), name='durable-recovery')
        log.info('SQLite otwarte; persistent views zarejestrowane; komendy zsynchronizowane.')

    async def on_ready(self):
        log.info('GOTOWY: %s (%s). on_ready nie tworzy zasobów.', self.user, self.user.id)

    async def on_disconnect(self):
        log.warning('Utracono połączenie z Discordem; biblioteka podejmie reconnect.')

    async def on_resumed(self):
        log.info('Sesja Discord wznowiona.')

    async def on_member_join(self, member):
        if not self.stopping and member.guild.id == self.config.ids['GUILD_ID']:
            async with self.operations:
                if not self.stopping:
                    await self.welcome.join(member)

    async def on_raw_member_remove(self, payload):
        if not self.stopping and payload.guild_id == self.config.ids['GUILD_ID']:
            guild = self.get_guild(payload.guild_id)
            if guild:
                async with self.operations:
                    if not self.stopping:
                        await self.welcome.refresh(guild)

    async def on_error(self, event, *args, **kwargs):
        log.exception('Błąd zdarzenia %s', event)

    async def close(self):
        if self.stopping:
            return
        self.stopping = True
        log.info('Graceful shutdown: zatrzymanie zadań, Discorda i SQLite.')
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)
        await super().close()
        # Wait for in-flight mutations before closing the database.
        async with self.operations:
            await self.db.close()

    def support(self, guild):
        role = guild.get_role(self.config.ids['SUPPORT_ROLE_ID'])
        if not role:
            raise ValueError('Brak skonfigurowanej roli Support.')
        return role

    def check(self, i, admin=False):
        if self.stopping:
            raise ValueError('Bot jest zatrzymywany. Spróbuj po restarcie.')
        if not i.guild or i.guild.id != self.config.ids['GUILD_ID']:
            raise ValueError('Ta funkcja działa tylko na skonfigurowanym serwerze.')
        if admin and not staff(i.user, self.support(i.guild)):
            raise ValueError('Wymagana rola Support lub wyższa.')

    async def marked_message(self, channel, marker, saved=None):
        if saved:
            try:
                return await channel.fetch_message(int(saved))
            except discord.NotFound:
                pass
        # Full scan only during setup/recovery, never per on_ready.
        async for message in channel.history(limit=None):
            if message.author.id == self.user.id and any(e.footer.text and any(e.footer.text.endswith(' • ' + m) for m in compatible_markers(marker)) for e in message.embeds):
                return message
        return None

    async def ensure_panel(self, guild, kind):
        channel = guild.get_channel(self.config.ids['TICKET_PANEL_CHANNEL_ID' if kind == 'ticket' else 'VERIFY_CHANNEL_ID'])
        if not isinstance(channel, discord.TextChannel):
            raise ValueError('Brak kanału panelu.')
        saved = await self.db.get('panel', kind) or {}
        marker = f'imbirxhc:panel:{kind}'
        message = await self.marked_message(channel, marker, saved.get('message'))
        e = embed('🎫 CENTRUM POMOCY • imbirxhc' if kind == 'ticket' else '✅ WERYFIKACJA • imbirxhc',
                  'Potrzebujesz pomocy? Utwórz prywatny ticket.' if kind == 'ticket' else 'Aby uzyskać dostęp do serwera, kliknij przycisk poniżej.', marker)
        if message:
            await message.edit(embed=e, view=Persistent(self, kind))
        else:
            message = await channel.send(embed=e, view=Persistent(self, kind))
        await self.db.put('panel', kind, {'channel': channel.id, 'message': message.id})

    async def action(self, action, i):
        try:
            self.check(i)
            if action == 'create':
                return await i.response.send_message('Wybierz typ zgłoszenia.', view=Choice(self, i.user.id), ephemeral=True)
            if action == 'close':
                self.check(i, admin=True)
                return await i.response.send_message('Wybierz powód zamknięcia.', view=Choice(self, i.user.id, True), ephemeral=True)
            await i.response.defer(ephemeral=True)
            async with self.operations:
                if action == 'verify':
                    role = i.guild.get_role(self.config.ids['PLAYER_ROLE_ID'])
                    if not role or role.managed or role >= i.guild.me.top_role or not i.guild.me.guild_permissions.manage_roles:
                        raise ValueError('Bot nie może nadać skonfigurowanej roli gracza.')
                    if role in i.user.roles:
                        return await reply(i, '✅ Jesteś już zweryfikowany.')
                    await i.user.add_roles(role, reason='Weryfikacja imbirxhc')
                    await reply(i, '✅ Zweryfikowano.')
                elif action in ('yes', 'no'):
                    record = await self.db.get('proposal', i.message.id)
                    if not record:
                        raise ValueError('Brak propozycji w bazie. Skontaktuj się z administracją.')
                    # Persist dirty BEFORE edit; recovery repairs counts after crash/API failure.
                    record['dirty'] = True
                    await self.db.put('proposal', i.message.id, record)
                    await self.db.vote(i.message.id, i.user.id, 1 if action == 'yes' else -1)
                    await i.message.edit(view=Persistent(self, 'vote', await self.db.counts(i.message.id)))
                    record['dirty'] = False
                    await self.db.put('proposal', i.message.id, record)
                    await reply(i, 'Zapisano głos.')
                elif action == 'claim':
                    self.check(i, admin=True)
                    key, ticket = await self.ticket_at(i.channel_id)
                    if ticket['status'] != 'open' or ticket.get('claimed'):
                        raise ValueError('Ticket jest już zajęty lub zamykany.')
                    ticket['claimed'] = i.user.id
                    await self.db.put('ticket', key, ticket)
                    await i.channel.send(embed=embed('🛡️ TICKET PRZEJĘTY', f'Ticket został przejęty przez {i.user.mention}.'))
                    await reply(i, 'Zajęto ticket.')
        except (ValueError, discord.HTTPException) as exc:
            log.exception('Operacja %s nie powiodła się', action)
            await reply(i, str(exc) if isinstance(exc, ValueError) else 'Discord odrzucił operację. Sprawdź logi i uprawnienia.')

    async def ticket_at(self, channel_id):
        for key, ticket in await self.db.all('ticket'):
            if ticket.get('channel') == channel_id:
                return key, ticket
        raise ValueError('Nie znaleziono ticketa w bazie.')

    async def create_ticket(self, i, kind, answers=None):
        self.check(i)
        answers = validate_answers(kind, answers or {})
        async with self.operations:
            for key, ticket in await self.db.all('ticket'):
                if ticket['author'] == i.user.id and ticket['kind'] == kind and ticket['status'] != 'closed':
                    raise ValueError('Masz już aktywny lub oczekujący ticket tego typu.')
            key = uuid.uuid4().hex
            ticket = {'author': i.user.id, 'username': i.user.name, 'kind': kind, 'created': now(),
                      'status': 'creating', 'guild': i.guild.id, 'claimed': None, 'answers': answers}
            await self.db.put('ticket', key, ticket)
            await self.finish_create(i.guild, key, ticket)
            await reply(i, f'🎫 Ticket: <#{ticket["channel"]}>')

    async def finish_create(self, guild, key, ticket):
        channels = await guild.fetch_channels()
        marker = f'imbirxhc:ticket:{key}'
        existing = next((c for c in channels if isinstance(c, discord.TextChannel) and c.topic in compatible_markers(marker)), None)
        if existing:
            channel = existing
            category = next((c for c in channels if c.id == channel.category_id), None)
        else:
            member = await guild.fetch_member(ticket['author'])
            support = self.support(guild)
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False),
                          guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
                          member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)}
            for role in guild.roles:
                if role >= support:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            cat_record = await self.db.get('category', ticket['kind']) or {}
            category = next((c for c in channels if isinstance(c, discord.CategoryChannel) and c.id == cat_record.get('id')), None)
            if category is None:
                # Reserved deterministic name bridges Discord-create / SQLite-save crash gap.
                cat_name = f'imbirxhc-{guild.id}-{ticket["kind"]}'
                matches = [c for c in channels if isinstance(c, discord.CategoryChannel) and c.name in compatible_markers(cat_name)]
                if len(matches) > 1:
                    raise ValueError('Niejednoznaczne kategorie ticketów; sprawdź logi.')
                category = matches[0] if matches else await guild.create_category(cat_name, overwrites=overwrites, position=max((c.position for c in channels), default=0)+1)
                await self.db.put('category', ticket['kind'], {'id': category.id})
            channel = await guild.create_text_channel(channel_name(ticket['username']), category=category, topic=marker, overwrites=overwrites)
        ticket['channel'] = channel.id
        ticket['category'] = category.id if category else None
        await self.db.put('ticket', key, ticket)
        panel = await self.marked_message(channel, marker, ticket.get('panel'))
        if panel is None:
            card = embed(f'🎫 TICKET • {self.types[ticket["kind"]]}', f'Witaj <@{ticket["author"]}>.\nTwoje zgłoszenie zostało zapisane. Obsługa odpowie w tym kanale.' if ticket.get('answers') else f'Witaj <@{ticket["author"]}>.\nOpisz dokładnie swoją sprawę.', marker)
            panel = await channel.send(embed=add_answers(card, ticket), view=Persistent(self, 'inside'))
        ticket.update(status='open', panel=panel.id)
        await self.db.put('ticket', key, ticket)

    async def request_close(self, i, reason):
        self.check(i, admin=True)
        async with self.operations:
            key, ticket = await self.ticket_at(i.channel_id)
            if ticket['status'] != 'open':
                raise ValueError('Ticket jest już zamykany.')
            ticket.update(status='closing', closed_by=i.user.id, reason=reason, closed_at=now(),
                          close_after=(discord.utils.utcnow() + timedelta(seconds=3)).isoformat())
            await self.db.put('ticket', key, ticket)
            await reply(i, '🔒 Ticket zostanie zamknięty za 3 sekundy.')
            self.wake.set()

    async def finish_close(self, guild, key, ticket):
        if discord.utils.utcnow() < discord.utils.parse_time(ticket['close_after']):
            return
        try:
            channel = await guild.fetch_channel(ticket['channel'])
        except discord.NotFound:
            if not ticket.get('transcript'):
                log.error('Kanał %s usunięty zewnętrznie; brak możliwości odzyskania historii.', ticket['channel'])
            ticket['status'] = 'closed'
            await self.db.put('ticket', key, ticket)
            await self.cleanup_category(guild, ticket)
            return
        # Freeze author writes before capturing history. Staff should stop sending too.
        overwrites = channel.overwrites
        for principal, permissions in overwrites.items():
            if principal.id != guild.me.id:
                permissions.send_messages = False
                permissions.send_messages_in_threads = False
        await channel.edit(overwrites=overwrites, reason='Zamykanie ticketa i utrwalanie historii')
        path = self.config.data / 'transcripts' / ticket.get('transcript', f'imbirxhc-{key}.html')
        path.parent.mkdir(exist_ok=True)
        if not ticket.get('transcript') or not path.exists():
            lines = ['<!doctype html><html lang="pl"><meta charset="utf-8"><title>imbirxhc Transcript</title>',
                     '<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;background:#18191c;color:#eee}article{border-bottom:1px solid #555;padding:12px}pre{white-space:pre-wrap}a{color:#8ac}</style>',
                     f'<h1>{html.escape(channel.name)}</h1><pre>{html.escape(str(ticket))}</pre>']
            async for message in channel.history(limit=None, oldest_first=True):
                lines.append(f'<article><b>{html.escape(str(message.author))} ({message.author.id})</b> · {message.created_at.isoformat()}<pre>{html.escape(message.content)}</pre>')
                for e in message.embeds:
                    lines.append(f'<pre>{html.escape(str(e.to_dict()))}</pre>')
                for attachment in message.attachments:
                    lines.append(f'<p><a href="{html.escape(attachment.url, quote=True)}">{html.escape(attachment.filename)}</a></p>')
                lines.append('</article>')
            lines.append('</html>')
            temporary = path.with_suffix('.tmp')
            await asyncio.to_thread(temporary.write_text, '\n'.join(lines), encoding='utf-8')
            await asyncio.to_thread(temporary.replace, path)
            ticket['transcript'] = str(path.name)
            await self.db.put('ticket', key, ticket)
        if not ticket.get('dm_done'):
            try:
                user = await self.fetch_user(ticket['author'])
                await user.send('Transcript Twojego ticketa imbirxhc.', file=discord.File(path))
            except discord.HTTPException:
                log.warning('Nie można wysłać DM/transcriptu dla %s; kopia pozostaje na dysku.', key)
            ticket['dm_done'] = True
            await self.db.put('ticket', key, ticket)
        log_id = self.config.ids['TICKET_LOG_CHANNEL_ID']
        if log_id and not ticket.get('log_done'):
            log_channel = await self.fetch_channel(log_id)
            marker = f'imbirxhc:transcript:{key}'
            old = await self.marked_message(log_channel, marker)
            if not old:
                await log_channel.send(embed=embed('🎫 ZAMKNIĘTY TICKET', f'Autor: <@{ticket["author"]}>\nPowód: {ticket["reason"]}', marker), file=discord.File(path))
            ticket['log_done'] = True
            await self.db.put('ticket', key, ticket)
        await channel.delete(reason=f'imbirxhc: {ticket["reason"]}')
        ticket['status'] = 'closed'
        await self.db.put('ticket', key, ticket)
        await self.cleanup_category(guild, ticket)

    async def cleanup_category(self, guild, ticket):
        record = await self.db.get('category', ticket['kind'])
        if not record or record['id'] != ticket.get('category'):
            return
        channels = await guild.fetch_channels()
        category = next((c for c in channels if c.id == record['id']), None)
        if category and not any(getattr(c, 'category_id', None) == category.id for c in channels):
            await category.delete(reason='Ostatni ticket zamknięty')

    async def on_message(self, message):
        if self.stopping or message.author.bot or not message.guild or message.guild.id != self.config.ids['GUILD_ID'] or message.channel.id != self.config.ids['SUGGESTIONS_CHANNEL_ID']:
            return
        async with self.operations:
            record = await self.db.get('source', message.id)
            if record:
                return
            record = {'author': message.author.id, 'content': message.content, 'attachments': [a.url for a in message.attachments],
                      'channel': message.channel.id, 'created': now(), 'status': 'pending'}
            await self.db.put('source', message.id, record)
            await self.publish_proposal(message.channel, str(message.id), record)

    async def publish_proposal(self, channel, source_id, record):
        marker = f'imbirxhc:proposal:{source_id}'
        message = await self.marked_message(channel, marker, record.get('message'))
        if not message:
            description = f'👤 Autor: <@{record["author"]}>\n\n**Propozycja**\n{record["content"] or "(załącznik)"}'
            e = embed('💡 NOWA PROPOZYCJA', description[:4096], marker)
            for n, url in enumerate(record['attachments'][:10]):
                e.add_field(name=f'Załącznik {n+1}', value=url[:1024], inline=False)
            extra = {}
            if len(description) > 4096:
                extra['file'] = discord.File(io.BytesIO(record['content'].encode('utf-8')), filename='pelna-propozycja.txt')
            message = await channel.send(embed=e, view=Persistent(self, 'vote'), **extra)
        await self.db.put('proposal', message.id, {**record, 'dirty': True, 'source': source_id})
        record.update(message=message.id, status='published')
        await self.db.put('source', source_id, record)
        try:
            original = await channel.fetch_message(int(source_id))
            await original.delete()
        except discord.NotFound:
            pass
        record['status'] = 'done'
        await self.db.put('source', source_id, record)

    async def maintenance(self):
        await self.wait_until_ready()
        guild = self.get_guild(self.config.ids['GUILD_ID'])
        if guild:
            for name in ('SUPPORT_ROLE_ID', 'PLAYER_ROLE_ID'):
                if not guild.get_role(self.config.ids[name]):
                    log.error('Brak roli z konfiguracji: %s', name)
            for name, identifier in self.config.ids.items():
                if 'CHANNEL_ID' in name and identifier and not guild.get_channel(identifier):
                    log.error('Brak kanału z konfiguracji: %s', name)
            if not self.config.staff:
                log.warning('STAFF_ROLE_IDS puste: degradacja pozostaje zablokowana.')
            else:
                try:
                    validate_staff_roles(guild, self.config.staff)
                except ValueError as exc:
                    log.error('%s', exc)
        while not self.stopping:
            self.wake.clear()
            try:
                await self.wait_until_ready()
                guild = self.get_guild(self.config.ids['GUILD_ID'])
                if not guild:
                    raise ValueError('Bot nie znajduje skonfigurowanego serwera.')
                async with self.operations:
                    try:
                        await self.welcome.recover(guild)
                        await self.welcome.refresh(guild)
                    except Exception:
                        log.exception('Powitania: błąd aktualizacji; ponowienie w następnym cyklu.')
                for key, _ in await self.db.all('ticket'):
                    async with self.operations:
                        ticket = await self.db.get('ticket', key)
                        try:
                            if ticket['status'] == 'creating':
                                await self.finish_create(guild, key, ticket)
                            elif ticket['status'] == 'closing':
                                await self.finish_close(guild, key, ticket)
                        except Exception:
                            log.exception('Odzyskiwanie ticketa %s nieudane; kolejna próba za 15 s.', key)
                for source, _ in await self.db.all('source'):
                    async with self.operations:
                        record = await self.db.get('source', source)
                        if record['status'] != 'done':
                            try:
                                await self.publish_proposal(await self.fetch_channel(record['channel']), source, record)
                            except Exception:
                                log.exception('Odzyskiwanie propozycji %s', source)
                # Counts come exclusively from SQLite, including after restart.
                for key, _ in await self.db.all('proposal'):
                    async with self.operations:
                        record = await self.db.get('proposal', key)
                        if record.get('dirty'):
                            try:
                                channel = await self.fetch_channel(record['channel'])
                                message = await channel.fetch_message(int(key))
                                await message.edit(view=Persistent(self, 'vote', await self.db.counts(key)))
                                record['dirty'] = False
                                await self.db.put('proposal', key, record)
                            except discord.NotFound:
                                record['dirty'] = False
                                await self.db.put('proposal', key, record)
                                log.warning('Propozycja %s została usunięta z Discorda; zachowano bazę.', key)
                            except Exception:
                                log.exception('Aktualizacja liczników %s', key)
                # Also repair a crash between channel deletion and category cleanup.
                for kind, category in await self.db.all('category'):
                    async with self.operations:
                        try:
                            await self.cleanup_category(guild, {'kind': kind, 'category': category['id']})
                        except discord.HTTPException:
                            log.exception('Sprzątanie pustej kategorii %s', kind)
                for key, record in await self.db.all('demotion'):
                    if record['status'] == 'applied' and not record.get('log_done'):
                        async with self.operations:
                            record = await self.db.get('demotion', key)
                            if not record.get('log_done'):
                                try:
                                    await self.log_demotion(key, record)
                                except discord.HTTPException:
                                    log.exception('Ponowienie logu degradacji %s', key)
            except Exception:
                log.exception('Błąd cyklu odzyskiwania')
            closing = any(t['status'] == 'closing' for _, t in await self.db.all('ticket'))
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=3 if closing else 15)
            except asyncio.TimeoutError:
                pass

    async def log_demotion(self, key, record):
        channel = await self.fetch_channel(self.config.ids['PUNISHMENTS_CHANNEL_ID'])
        marker = f'imbirxhc:demotion:{key}'
        if not await self.marked_message(channel, marker):
            old = ', '.join(f'<@&{role}>' for role in record['old'])
            e = embed('🔨 DEGRADACJA CZŁONKA ADMINISTRACJI', f'👤 Użytkownik: <@{record["target"]}>\n📉 Poprzednia ranga: {old}\n📉 Nowa ranga: <@&{record["new"]}>\n📝 Powód: {record["reason"]}\n👮 Moderator: <@{record["actor"]}>\n🕒 Data: {record["at"]}', marker)
            if record.get('avatar'):
                e.set_thumbnail(url=record['avatar'])
            await channel.send(embed=e)
        record['log_done'] = True
        await self.db.put('demotion', key, record)

    def register_commands(self):
        @self.tree.error
        async def command_error(i, error):
            cause = getattr(error, 'original', error)
            log.error('Błąd komendy', exc_info=cause)
            await reply(i, str(cause) if isinstance(cause, ValueError) else 'Operacja nie powiodła się. Sprawdź uprawnienia i logi.')

        @self.tree.command(name='setup', description='Utwórz lub odśwież panele imbirxhc')
        @app_commands.guild_only()
        @app_commands.default_permissions(administrator=True)
        async def setup(i: discord.Interaction):
            self.check(i)
            if i.user.id != i.guild.owner_id and not i.user.guild_permissions.administrator:
                raise ValueError('Wymagany właściciel serwera lub Administrator.')
            await i.response.defer(ephemeral=True)
            async with self.operations:
                await self.ensure_panel(i.guild, 'ticket')
                await self.ensure_panel(i.guild, 'verify')
            await reply(i, 'Panele gotowe.')

        @self.tree.command(name='mute', description='Timeout z potwierdzeniem')
        @app_commands.guild_only()
        async def mute(i: discord.Interaction, użytkownik: discord.Member, czas: str, powód: str):
            self.check(i, admin=True)
            seconds = duration(czas)
            if len(powód) > 400:
                raise ValueError('Powód może mieć maksymalnie 400 znaków.')
            hierarchy(i.user, użytkownik, i.guild.me)
            async def apply(confirm):
                async with self.operations:
                    actor = await i.guild.fetch_member(i.user.id)
                    target = await i.guild.fetch_member(użytkownik.id)
                    if not staff(actor, self.support(i.guild)):
                        raise ValueError('Nie masz już uprawnień Support+.')
                    hierarchy(actor, target, i.guild.me)
                    if not i.guild.me.guild_permissions.moderate_members or target.guild_permissions.administrator:
                        raise ValueError('Brak uprawnień do timeoutu tego użytkownika.')
                    await target.timeout(timedelta(seconds=seconds), reason=powód)
                    await self.db.put('mute', uuid.uuid4().hex, {'target': target.id, 'actor': actor.id, 'seconds': seconds, 'reason': powód, 'at': now()})
                    await reply(confirm, '🔇 Timeout zastosowany.')
            await i.response.send_message(embed=embed('🔇 POTWIERDZENIE WYCISZENIA', f'Użytkownik: {użytkownik.mention}\nDiscord ID: {użytkownik.id}\nCzas: {czas}\nPowód: {powód}\nModerator: {i.user.mention}'), view=Confirm(i.user.id, apply), ephemeral=True)

        @self.tree.command(name='degradacja', description='Zmień rangę administracyjną na niższą')
        @app_commands.guild_only()
        async def demote(i: discord.Interaction, użytkownik: discord.Member, ranga: discord.Role, powód: str):
            self.check(i, admin=True)
            if len(powód) > 400:
                raise ValueError('Powód może mieć maksymalnie 400 znaków.')
            await i.response.defer(ephemeral=True)
            async with self.operations:
                actor = await i.guild.fetch_member(i.user.id)
                target = await i.guild.fetch_member(użytkownik.id)
                if not staff(actor, self.support(i.guild)):
                    raise ValueError('Nie masz już uprawnień Support+.')
                hierarchy(actor, target, i.guild.me)
                # Validate the roles involved in this operation. Unrelated staff
                # order discrepancies must not block a valid multi-rank demotion.
                roles, old = demoted_roles(target.roles, ranga, self.config.staff, self.config.ids['PLAYER_ROLE_ID'])
                manageable_roles(actor, i.guild.me, old + [ranga])
                key = uuid.uuid4().hex
                record = {'target': target.id, 'actor': actor.id, 'old': [r.id for r in old], 'new': ranga.id, 'reason': powód, 'at': now(), 'status': 'pending', 'avatar': target.display_avatar.url}
                await self.db.put('demotion', key, record)
                await target.edit(roles=[r for r in roles if not r.is_default()], reason=powód)
                record['status'] = 'applied'
                await self.db.put('demotion', key, record)
                try:
                    await self.log_demotion(key, record)
                except discord.HTTPException:
                    log.exception('Degradacja wykonana; nie udało się wysłać logu %s', key)
                    return await reply(i, 'Degradacja wykonana i zapisana w SQLite. Nie udało się wysłać logu na kanał kar.')
                await reply(i, 'Degradacja wykonana; inne role zachowano.')
