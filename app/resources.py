# app/resources.py
"""Модуль ресурсов приложения"""

import os
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize

# Путь к иконке
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(BASE_DIR, "icon.png")
ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")

# Сет иконок разделов Tray S.: имя -> файл SVG.
# Вариант "dark" — светлый контур для тёмного меню/трея (*.svg),
# вариант "light" — тёмный контур для светлой темы (*_light.svg).
SECTION_ICONS = {
    "session": "session",
    "games": "games",
    "alarms": "alarms",
    "timer": "timer",
    "settings": "settings",
    "about_tray": "about_tray",
}

# Кэш: файл читается и декодируется один раз, а не при каждом вызове
_icon_cache = None
_pixmap_cache = {}
_section_icon_cache = {}


def get_app_icon() -> QIcon:
    """Возвращает иконку приложения (кэшируется)."""
    global _icon_cache
    if _icon_cache is None:
        if os.path.exists(ICON_PATH):
            _icon_cache = QIcon(ICON_PATH)
        else:
            _icon_cache = QIcon()
    return _icon_cache


def get_app_pixmap(size: int = 100) -> QPixmap:
    """Возвращает pixmap иконки заданного размера (кэшируется по размеру)."""
    if size not in _pixmap_cache:
        pixmap = QPixmap(ICON_PATH)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        _pixmap_cache[size] = pixmap
    return _pixmap_cache[size]


def _section_svg_path(name: str, theme: str) -> str:
    """Путь к SVG раздела: theme 'dark' — для тёмного фона, 'light' — для светлого."""
    base = SECTION_ICONS.get(name, name)
    suffix = "" if theme == "dark" else "_light"
    candidate = os.path.join(ICONS_DIR, f"{base}{suffix}.svg")
    if os.path.exists(candidate):
        return candidate
    # Запасной путь: PNG 32px того же варианта, затем любой существующий файл
    for fallback in (
        os.path.join(ICONS_DIR, "png", theme, f"{base}_32.png"),
        os.path.join(ICONS_DIR, f"{base}.svg"),
    ):
        if os.path.exists(fallback):
            return fallback
    return ""


def get_section_icon(name: str, theme: str = "dark") -> QIcon:
    """Иконка раздела Tray S. (session/games/alarms/timer/settings/about_tray).

    theme совпадает с темой приложения: 'dark' — светлый контур для
    тёмного меню, 'light' — тёмный контур для светлой темы.
    """
    key = (name, theme)
    if key not in _section_icon_cache:
        path = _section_svg_path(name, theme)
        _section_icon_cache[key] = QIcon(path) if path else QIcon()
    return _section_icon_cache[key]


def get_section_pixmap(name: str, size: int = 32, theme: str = "dark") -> QPixmap:
    """Pixmap раздела заданного размера (для предпросмотра/кнопок)."""
    icon = get_section_icon(name, theme)
    if icon.isNull():
        return QPixmap()
    return icon.pixmap(QSize(size, size))
