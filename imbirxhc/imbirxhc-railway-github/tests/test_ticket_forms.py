from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from imbirxhc.client import ImbirBot, embed
from imbirxhc.config import Config
from imbirxhc.rules import demoted_roles
from imbirxhc.ticket_forms import FIELDS, TicketForm, add_answers, validate_answers
from test_configuration import Role, RANKS, IDS


@pytest.mark.parametrize('current', range(6))
def test_every_staff_rank_can_demote_to_player_without_duplicates(current):
    player = Role(IDS['PLAYER_ROLE_ID'], 1)
    cosmetic = Role(777, 2)
    old = Role(RANKS[current], current + 10)
    result, removed = demoted_roles([player, cosmetic, old], player, RANKS, player.id)
    assert result == [cosmetic, player] and removed == [old]


def test_player_cannot_be_demoted_again_and_arbitrary_role_rejected():
    player = Role(IDS['PLAYER_ROLE_ID'], 1)
    with pytest.raises(ValueError):
        demoted_roles([player], player, RANKS, player.id)
    with pytest.raises(ValueError):
        demoted_roles([Role(RANKS[4], 15)], Role(777, 1), RANKS, player.id)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['0', '1', '2', '3'])
async def test_form_required_fields_and_panel(kind, tmp_path):
    bot = ImbirBot(Config('', IDS, RANKS, tmp_path))
    try:
        form = TicketForm(bot, 10, kind)
        assert len(form.children) == (3 if kind in ('0', '3') else 1)
        assert all(field.required for field in form.children)
        answers = validate_answers(kind, {key: 'Przykładowa odpowiedź' for key, _, _ in FIELDS[kind]})
        card = add_answers(embed('TICKET'), {'kind': kind, 'answers': answers})
        assert [f.name for f in card.fields] == [label for _, label, _ in FIELDS[kind]]
        assert all(f.value == 'Przykładowa odpowiedź' for f in card.fields)
        with pytest.raises(ValueError):
            validate_answers(kind, {key: '   ' for key, _, _ in FIELDS[kind]})
    finally:
        await bot.close()


@pytest.mark.asyncio
async def test_ticket_form_answers_persist_before_discord_creation(tmp_path):
    bot = ImbirBot(Config('', IDS, RANKS, tmp_path))
    await bot.db.open()
    i = SimpleNamespace(guild=SimpleNamespace(id=IDS['GUILD_ID']), user=SimpleNamespace(id=77, name='tester'),
        response=SimpleNamespace(is_done=lambda: True), followup=SimpleNamespace(send=AsyncMock()))
    async def finish(guild, key, ticket):
        assert (await bot.db.get('ticket', key))['answers'] == {'description': 'Straciłem ekwipunek'}
        ticket['channel'] = 999
    bot.finish_create = AsyncMock(side_effect=finish)
    try:
        await bot.create_ticket(i, '2', {'description': 'Straciłem ekwipunek'})
        with pytest.raises(ValueError, match='aktywny'):
            await bot.create_ticket(i, '2', {'description': 'Druga próba'})
        assert bot.finish_create.await_count == 1
    finally:
        await bot.close()
    restarted = ImbirBot(Config('', IDS, RANKS, tmp_path))
    await restarted.db.open()
    try:
        records = await restarted.db.all('ticket')
        assert records[0][1]['answers']['description'] == 'Straciłem ekwipunek'
    finally:
        await restarted.close()
