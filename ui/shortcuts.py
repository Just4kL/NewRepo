# ui/shortcuts.py
"""Модуль горячих клавиш"""

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut


def init_shortcuts(parent) -> list:
    """Инициализация горячих клавиш."""
    shortcuts = []
    
    # Ctrl+T - переключение темы
    shortcut_theme = QShortcut(QKeySequence("Ctrl+T"), parent)
    shortcut_theme.activated.connect(parent.toggle_theme)
    shortcuts.append(shortcut_theme)
    
    # Ctrl+Up - увеличение шрифта
    shortcut_font_up = QShortcut(QKeySequence("Ctrl+Up"), parent)
    shortcut_font_up.activated.connect(parent.increase_font_size)
    shortcuts.append(shortcut_font_up)

    # Ctrl+Down - уменьшение шрифта
    shortcut_font_down = QShortcut(QKeySequence("Ctrl+Down"), parent)
    shortcut_font_down.activated.connect(parent.decrease_font_size)
    shortcuts.append(shortcut_font_down)

    # Ctrl+F - фокус на поиск
    shortcut_find = QShortcut(QKeySequence("Ctrl+F"), parent)
    shortcut_find.activated.connect(parent.focus_search)
    shortcuts.append(shortcut_find)

    # Ctrl+S - ручное сохранение
    shortcut_save = QShortcut(QKeySequence("Ctrl+S"), parent)
    shortcut_save.activated.connect(parent.manual_save_profile)
    shortcuts.append(shortcut_save)

    # F2 - ручное сохранение
    shortcut_save = QShortcut(QKeySequence("Ctrl+S"), parent)
    shortcut_save.activated.connect(parent.manual_save_profile)
    shortcuts.append(shortcut_save)

    return shortcuts