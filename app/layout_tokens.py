# app/layout_tokens.py
"""Токены лейаута: единый доступ к tokens/layout.json.

Единственное место, читающее файл токенов. Весь остальной код берёт
числа отсюда (space()/tokens()), магических чисел в коде нет.
"""

import json
import os

_CACHE = None


def _path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "tokens", "layout.json")


def tokens():
    """Весь словарь токенов (кэшируется)."""
    global _CACHE
    if _CACHE is None:
        with open(_path(), encoding="utf-8") as fh:
            _CACHE = json.load(fh)
    return _CACHE


def space(name):
    """Значение шкалы spacing: space("xs") -> 4."""
    return tokens()["space"][name]
