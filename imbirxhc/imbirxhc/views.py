import logging
import discord
from .compat import BRAND
from .ticket_forms import TicketForm

log = logging.getLogger(__name__)


async def reply(interaction, text):
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


class Persistent(discord.ui.View):
    def __init__(self, bot, kind, counts=None, namespace=BRAND):
        super().__init__(timeout=None)
        self.bot = bot
        actions = {
            'ticket': [('create', '🎫 STWÓRZ TICKET')],
            'verify': [('verify', '✅ ZWERYFIKUJ SIĘ')],
            'inside': [('claim', '🛡️ Zajmij ticket'), ('close', '🔒 Zamknij ticket')],
            'vote': [('yes', f'👍 ZA • {(counts or {}).get(1, 0)}'),
                     ('no', f'👎 PRZECIW • {(counts or {}).get(-1, 0)}')],
        }
        for action, label in actions[kind]:
            button = discord.ui.Button(label=label, custom_id=f'{namespace}:v1:{action}', style=discord.ButtonStyle.secondary)
            async def callback(i, action=action):
                await bot.action(action, i)
            button.callback = callback
            self.add_item(button)

    async def on_error(self, interaction, error, item):
        log.error('Błąd przycisku %s', item.custom_id, exc_info=error)
        await reply(interaction, 'Nie udało się wykonać operacji. Administracja może sprawdzić logi.')


class Choice(discord.ui.View):
    def __init__(self, bot, user_id, closing=False):
        super().__init__(timeout=120)
        self.user_id = user_id
        options = ['✅ Załatwione', '💬 Dostał odpowiedź', '⛔ Nie otrzymasz nic'] if closing else list(bot.types.values())
        select = discord.ui.Select(placeholder='Wybierz powód' if closing else 'Wybierz typ ticketa', options=[discord.SelectOption(label=v, value=str(n)) for n, v in enumerate(options)])
        async def callback(i):
            try:
                if closing:
                    await i.response.defer(ephemeral=True)
                    await bot.request_close(i, options[int(select.values[0])])
                else:
                    bot.check(i)
                    await i.response.send_modal(TicketForm(bot, i.user.id, str(int(select.values[0]))))
            except (ValueError, discord.HTTPException) as exc:
                log.exception('Błąd wyboru ticketa')
                await reply(i, str(exc) if isinstance(exc, ValueError) else 'Discord odrzucił operację. Sprawdź uprawnienia i logi.')
        select.callback = callback
        self.add_item(select)

    async def interaction_check(self, i):
        if i.user.id != self.user_id:
            await reply(i, 'To menu należy do innego użytkownika.')
            return False
        return True

    async def on_error(self, i, error, item):
        log.error('Błąd menu', exc_info=error)
        await reply(i, 'Operacja nie powiodła się. Sprawdź logi.')


class Confirm(discord.ui.View):
    def __init__(self, user_id, callback):
        super().__init__(timeout=120)
        self.user_id, self.apply, self.used = user_id, callback, False

    async def interaction_check(self, i):
        if i.user.id != self.user_id or self.used:
            await reply(i, 'Potwierdzenie jest niedostępne.')
            return False
        return True

    @discord.ui.button(label='✅ Potwierdź', style=discord.ButtonStyle.danger)
    async def yes(self, i, button):
        self.used = True
        await i.response.defer(ephemeral=True)
        try:
            await self.apply(i)
        except (ValueError, discord.HTTPException) as exc:
            await reply(i, str(exc) if isinstance(exc, ValueError) else 'Discord odrzucił operację.')
        finally:
            self.stop()
            await i.edit_original_response(view=None)

    @discord.ui.button(label='❌ Anuluj')
    async def no(self, i, button):
        self.used = True
        self.stop()
        await i.response.edit_message(content='Anulowano.', embed=None, view=None)
