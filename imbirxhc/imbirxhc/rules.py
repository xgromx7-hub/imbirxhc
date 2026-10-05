import re


def duration(value):
    match = re.fullmatch(r'([1-9][0-9]*)([smhd])', value)
    if not match:
        raise ValueError('Podaj czas np. 30s, 10m, 2h, 1d, 7d.')
    seconds = int(match[1]) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[match[2]]
    if seconds > 28 * 86400:
        raise ValueError('Maksymalny timeout to 28 dni.')
    return seconds


def channel_name(username):
    return 'ticket-' + (re.sub(r'[^a-z0-9-]', '-', username.lower()).strip('-')[:70] or 'gracz')


def staff(member, support):
    return support is not None and (member.id == member.guild.owner_id or member.top_role >= support)


def hierarchy(actor, target, bot):
    if target.id == target.guild.owner_id or target.id == bot.id:
        raise ValueError('Nie można moderować właściciela ani bota.')
    if target.top_role >= actor.top_role or target.top_role >= bot.top_role:
        raise ValueError('Użytkownik ma równą lub wyższą rolę od moderatora/bota.')


def demoted_roles(roles, target, configured, player_id=None):
    order = {identifier: index for index, identifier in enumerate(configured)}
    if player_id is not None:
        order[player_id] = -1
    old = [r for r in roles if r.id in configured]
    if (not old or target.id not in order
            or order[target.id] >= max(order[r.id] for r in old)
            or target >= max(old)):
        raise ValueError('Wybierz niższą rangę administracyjną lub rolę gracza. Docelowa rola musi być niższa także na Discordzie.')
    return [r for r in roles if r.id not in configured and r.id != target.id] + [target], old


def validate_staff_roles(guild, configured):
    roles = [guild.get_role(identifier) for identifier in configured]
    if not roles or any(role is None for role in roles):
        raise ValueError('Brak jednej ze skonfigurowanych rang administracyjnych. Sprawdź ID.')
    if any(low >= high for low, high in zip(roles, roles[1:])):
        raise ValueError('Hierarchia ról Discorda jest niezgodna z kolejnością STAFF_ROLE_IDS. Popraw kolejność ról na serwerze.')
    return roles


def manageable_roles(actor, bot, roles):
    if not bot.guild_permissions.manage_roles or any(
        r.managed or r >= bot.top_role or r >= actor.top_role or r.is_default() for r in roles
    ):
        raise ValueError('Nie można zarządzać wskazanymi rangami.')
