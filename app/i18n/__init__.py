# app/i18n/__init__.py
"""Модуль локализации с глобальным доступом (12 языков)."""

from app.config import LANGUAGES

from .ru import TRANSLATIONS_RU
from .en import TRANSLATIONS_EN
from .es import TRANSLATIONS_ES
from .de import TRANSLATIONS_DE
from .ja import TRANSLATIONS_JA
from .zh import TRANSLATIONS_ZH
from .pt import TRANSLATIONS_PT
from .cs import TRANSLATIONS_CS
from .pl import TRANSLATIONS_PL
from .uk import TRANSLATIONS_UK
from .hi import TRANSLATIONS_HI
from .la import TRANSLATIONS_LA
from .fr import TRANSLATIONS_FR
from .ar import TRANSLATIONS_AR
from .id import TRANSLATIONS_ID

TRANSLATIONS = {
    "ru": TRANSLATIONS_RU,
    "en": TRANSLATIONS_EN,
    "es": TRANSLATIONS_ES,
    "de": TRANSLATIONS_DE,
    "ja": TRANSLATIONS_JA,
    "zh": TRANSLATIONS_ZH,
    "pt": TRANSLATIONS_PT,
    "cs": TRANSLATIONS_CS,
    "pl": TRANSLATIONS_PL,
    "uk": TRANSLATIONS_UK,
    "hi": TRANSLATIONS_HI,
    "la": TRANSLATIONS_LA,
    "fr": TRANSLATIONS_FR,
    "ar": TRANSLATIONS_AR,
    "id": TRANSLATIONS_ID,
}

# Имя языка (как в LANGUAGES) -> код. Принимаем и коды напрямую.
NAME2CODE = {lang["name"]: lang["code"] for lang in LANGUAGES}

_current_language = "Русский"
_current_code = "ru"
_current_translation = TRANSLATIONS["ru"]


def set_language(language: str):
    """Устанавливает текущий язык (имя из LANGUAGES или код)."""
    global _current_language, _current_code, _current_translation
    code = NAME2CODE.get(language, language)
    if code not in TRANSLATIONS:
        code = "ru"
    _current_code = code
    _current_translation = TRANSLATIONS[code]
    _current_language = next(
        (lang["name"] for lang in LANGUAGES if lang["code"] == code),
        "Русский",
    )


def get_language_code() -> str:
    """Код текущего языка (ru/en/es/...)."""
    return _current_code


def get_language_name() -> str:
    """Имя текущего языка."""
    return _current_language


def tr(key: str) -> str:
    """Возвращает перевод по ключу."""
    return _current_translation.get(key, key)


def get_translation(language: str = None) -> dict:
    """Возвращает словарь переводов."""
    if language:
        code = NAME2CODE.get(language, language)
        return TRANSLATIONS.get(code, TRANSLATIONS["ru"])
    return _current_translation
