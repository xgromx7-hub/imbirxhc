import logging
import discord

log = logging.getLogger(__name__)

FIELDS = {
    '0': [('reporter', 'Nick osoby zgłaszającej', 64),
          ('reported', 'Nick zgłaszanego gracza', 64),
          ('description', 'Opis sytuacji', 1000)],
    '1': [('description', 'Opis sytuacji', 1000)],
    '2': [('description', 'Opis całej sytuacji', 1000)],
    '3': [('moderator', 'Nick osoby nakładającej bana', 64),
          ('player', 'Twój nick w grze', 64),
          ('reason', 'Powód otrzymania bana', 1000)],
}


def validate_answers(kind, answers):
    if kind not in FIELDS:
        raise ValueError('Nieprawidłowy typ ticketa.')
    cleaned = {}
    for key, label, limit in FIELDS[kind]:
        value = str(answers.get(key, '')).strip()
        if not value or len(value) > limit:
            raise ValueError(f'Pole „{label}” jest wymagane (maks. {limit} znaków).')
        cleaned[key] = value
    return cleaned


def add_answers(embed, ticket):
    for key, label, _ in FIELDS.get(ticket['kind'], []):
        value = ticket.get('answers', {}).get(key)
        if value:
            embed.add_field(name=label, value=discord.utils.escape_markdown(value)[:1024], inline=False)
    return embed


class TicketForm(discord.ui.Modal):
    def __init__(self, bot, user_id, kind):
        super().__init__(title=bot.types[kind], timeout=600)
        self.bot, self.user_id, self.kind = bot, user_id, kind
        self.inputs = {}
        for key, label, limit in FIELDS[kind]:
            field = discord.ui.TextInput(label=label, required=True, max_length=limit,
                style=discord.TextStyle.paragraph if limit > 64 else discord.TextStyle.short)
            self.inputs[key] = field
            self.add_item(field)

    async def on_submit(self, i):
        from .views import reply
        if i.user.id != self.user_id:
            return await reply(i, 'Ten formularz należy do innej osoby.')
        await i.response.defer(ephemeral=True)
        try:
            answers = validate_answers(self.kind, {k: f.value for k, f in self.inputs.items()})
            await self.bot.create_ticket(i, self.kind, answers)
        except ValueError as exc:
            await reply(i, str(exc))
        except discord.HTTPException:
            log.exception('Nie udało się utworzyć ticketa z formularza')
            await reply(i, 'Nie udało się zakończyć operacji. Sprawdź logi; zapisane zgłoszenie zostanie ponowione.')

    async def on_error(self, i, error):
        from .views import reply
        log.error('Błąd formularza ticketa', exc_info=error)
        await reply(i, 'Nie udało się zapisać zgłoszenia. Spróbuj ponownie.')
