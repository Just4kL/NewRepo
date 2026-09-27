# app/resources.py
"""Модуль ресурсов приложения"""

import os
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize

# Путь к иконке
ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.png")

# Кэш: файл читается и декодируется один раз, а не при каждом вызове
_icon_cache = None
_pixmap_cache = {}


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
