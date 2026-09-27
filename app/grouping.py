# app/grouping.py
"""Группировка игр в серии (Warhammer 40k, Borderlands, ...).

Чистый модуль без Qt: по названию вычисляет базу серии, игры с общей
базой (2+) складываются в группу с агрегированным временем.
Одиночные игры идут обычными строками.
"""

import re

# Разделитель подзаголовка: "X: Y", "X - Y", "X | Y", "X (1993)"
_SPLIT_RE = re.compile(r"\s*[:|–—]\s*|\s+-\s+|\s+\(")
# Висячий номер/том в конце: "Borderlands 2", "Civilization VI", "FIFA 24"
_TRAILING_NUM_RE = re.compile(r"\s+(\d+|[IVXLCDM]+)$", re.IGNORECASE)
# Висячее название издания: "Skyrim Special Edition", "Metro 2033 Redux"
_EDITION_SUFFIXES = (
    "game of the year edition",
    "definitive edition",
    "complete edition",
    "enhanced edition",
    "legendary edition",
    "special edition",
    "anniversary edition",
    "deluxe edition",
    "ultimate edition",
    "gold edition",
    "goty",
    "remastered",
    "remake",
    "enhanced",
    "redux",
    "collection",
    "hd",
)


def series_base_name(title: str) -> str:
    """База серии для названия игры.

    Warhammer 40,000: Space Marine 2 -> Warhammer 40,000
    Borderlands 2 -> Borderlands
    Baldur's Gate 3 -> Baldur's Gate
    DOOM (1993) -> DOOM
    """
    if not title:
        return ""
    base = _SPLIT_RE.split(title.strip(), maxsplit=1)[0].strip()
    # Снимаем издание и номер по кругу: "X 2 GOTY" -> "X 2" -> "X"
    for _ in range(3):
        low = base.lower()
        stripped = False
        for ed in _EDITION_SUFFIXES:
            if low.endswith(" " + ed):
                base = base[:-(len(ed) + 1)].strip()
                low = base.lower()
                stripped = True
                break
        new_base = _TRAILING_NUM_RE.sub("", base).strip()
        if new_base != base:
            base = new_base
            stripped = True
        if not stripped:
            break
    return base


def group_games(games):
    """Группирует список игр в entries.

    Возвращает [{"kind": "game", "game": g}] для одиночек и
    [{"kind": "group", "agg": {...}, "members": [...]}] для серий (2+).
    Порядок: первое появление базы. Агрегат формой как игра, поэтому
    существующие ключи сортировки работают и для групп.
    """
    buckets = {}
    order = []
    for game in games:
        base = series_base_name(game.get("name", ""))
        if len(base) < 2:
            base = game.get("name", "") or "?"
        key = base.lower()
        if key not in buckets:
            buckets[key] = {"name": base, "members": []}
            order.append(key)
        buckets[key]["members"].append(game)

    entries = []
    for key in order:
        bucket = buckets[key]
        members = bucket["members"]
        if len(members) == 1:
            entries.append({"kind": "game", "game": members[0]})
        else:
            entries.append({"kind": "group",
                            "agg": aggregate_group(bucket["name"], members),
                            "members": members})
    return entries


def _known_min(values):
    known = [v for v in values if v and v != "?"]
    return min(known) if known else "?"


def _known_max(values):
    known = [v for v in values if v and v != "?"]
    return max(known) if known else "?"


def aggregate_group(name, members):
    """Агрегат группы той же формы, что игра."""
    playtime = sum(m.get("playtime_forever", 0) for m in members)
    unlocked = sum(m.get("achievements", {}).get("unlocked", 0) for m in members)
    total = sum(m.get("achievements", {}).get("total", 0) for m in members)
    methods = {m.get("acquire_method", "?") for m in members}
    return {
        "appid": min([m.get("appid", 0) for m in members] or [0]),
        "name": name,
        "hours": round(playtime / 60, 2),
        "minutes": round(float(playtime), 2),
        "acquired": _known_min([m.get("acquired", "?") for m in members]),
        "achievements": {"unlocked": unlocked, "total": total},
        "last_played": _known_max([m.get("last_played", "?") for m in members]),
        "acquire_method": next(iter(methods)) if len(methods) == 1 else "—",
        "playtime_forever": playtime,
        "share": round(sum(m.get("share", 0.0) for m in members), 2),
    }
