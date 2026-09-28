# ui/gui.py
"""Единый GUI-агрегатор приложения.

Собирает в одном месте всё, что касается интерфейса:
окна и диалоги, темы и стили, шрифты, язык, меню, горячие клавиши,
фабрики типовых элементов (кнопка языка, переключатель сетки).

Общий визуальный стиль берётся из ui.styles — агрегатор его не меняет,
а только применяет. Бизнес-логика (Steam API, кэш, экспорт) остаётся
в MainWindow и app/*.
"""

from typing import Callable, Dict, Optional

from PyQt5.QtWidgets import QApplication, QToolButton, QStyleFactory, QAction
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from app.i18n import tr
from app.resources import get_section_icon
from ui.styles import apply_theme as _apply_theme, get_app_styles
from ui import dialogs as _dialogs
from ui.shortcuts import init_shortcuts as _init_shortcuts


# ==================== ДИЗАЙН-ТОКЕНЫ ====================
# Единые параметры сетки и карточек. Все новые экраны берут их отсюда,
# а не хардкодят отступы по месту.

DESIGN = {
    "spacing": 6,                 # отступы между карточками сетки
    "margins": (8, 8, 8, 8),      # поля корневого layout
    "radius": 10,                 # скругление карточек
    "profile_max_height": 176,    # потолок карточки профиля (сетка 2x2 + подписи)
    "avatar_size": 48,            # компактный аватар
    "action_button": (200, 32),   # ширина/высота кнопки «Посчитать время» (запас под длинные языки)
    "narrow_breakpoint": 900,     # уже — сетка складывается в одну колонку
    "wide_stretches": (3, 2),     # пропорции колонок: контент | профиль
}

# Единое хранилище лёгких настроек (скрытые колонки, API-ключ,
# SteamID, состояние сетки). Windows → реестр, Linux → ini.
SETTINGS_ORG = "KenigTheodor"
SETTINGS_APP = "SteamPlaytimeViewer"

# Реестр диалогов: имя -> функция показа. Новые окна регистрируются здесь,
# а вызываются одной строкой: gui.show_dialog("about").
DIALOGS: Dict[str, Callable] = {
    "font": _dialogs.show_font_dialog,
    "about": _dialogs.show_about_dialog,
    "changelog": _dialogs.show_changelog_dialog,
    "docs": _dialogs.show_documentation_dialog,
    "shortcuts": _dialogs.show_shortcuts_dialog,
}


class Gui:
    """Фасад интерфейса, привязанный к главному окну.

    Хранит ссылки на chrome-элементы (кнопка языка, переключатель сетки)
    и умеет их переводить при смене языка.
    """

    def __init__(self, window):
        self._w = window
        self._language_btn: Optional[QToolButton] = None
        self._layout_btn: Optional[QToolButton] = None
        self._dashboard = None

    # ==================== ТЕМА / СТИЛИ / ШРИФТ ====================

    def apply_theme(self, theme: str):
        """Применяет палитру и таблицы стилей."""
        _apply_theme(QApplication.instance(), theme)
        self._w.setStyleSheet(get_app_styles(theme))

    def apply_font_settings(self):
        """Применяет шрифт ко всему дереву виджетов."""
        from PyQt5.QtWidgets import QWidget  # локально против циклов
        w = self._w
        font = QFont(w.font_family, w.font_size)
        if w.font_bold:
            font.setBold(True)
        if w.font_italic:
            font.setItalic(True)
        QApplication.instance().setFont(font)
        if hasattr(w, "table_section"):
            w.table_section.table.setFont(font)
            w.table_section.table.horizontalHeader().setFont(font)
        for widget in w.findChildren(QWidget):
            widget.setFont(font)
        # Rich-текст и акцентные размеры не берутся из setFont —
        # перерисовываем типографику профиля под новый шрифт
        if hasattr(w, "profile_section"):
            w.profile_section.refresh_type_scale()

    # ==================== МЕНЮ ====================

    def build_menu(self):
        """Строит главное меню (Файл / Настройки / Справка)."""
        w = self._w
        theme = getattr(w, "theme", "dark")
        menubar = w.menuBar()

        # Файл
        file_menu = menubar.addMenu(tr("menu_file"))
        open_action = QAction(tr("menu_open"), w)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(w.open_profile)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        export_csv_action = QAction(tr("menu_export_csv"), w)
        export_csv_action.setShortcut("Ctrl+E")
        export_csv_action.triggered.connect(w.export_csv)
        file_menu.addAction(export_csv_action)
        export_xlsx_action = QAction(tr("menu_export_xlsx"), w)
        export_xlsx_action.triggered.connect(w.export_xlsx)
        file_menu.addAction(export_xlsx_action)
        file_menu.addSeparator()
        exit_action = QAction(tr("menu_exit"), w)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(w.close)
        file_menu.addAction(exit_action)

        # Настройки
        settings_menu = menubar.addMenu(tr("menu_settings"))
        theme_menu = settings_menu.addMenu(tr("menu_theme"))
        light_action = QAction(tr("menu_light"), w)
        light_action.triggered.connect(lambda: w.set_theme("light"))
        theme_menu.addAction(light_action)
        dark_action = QAction(tr("menu_dark"), w)
        dark_action.triggered.connect(lambda: w.set_theme("dark"))
        theme_menu.addAction(dark_action)
        font_action = QAction(tr("menu_font"), w)
        font_action.setIcon(get_section_icon("settings", theme))
        font_action.triggered.connect(lambda: self.show_dialog("font"))
        settings_menu.addAction(font_action)

        # Вид — переключаемые колонки таблицы
        view_menu = menubar.addMenu(tr("menu_view"))
        for _key, _label_key in (("acquired", "show_acquired_col"),
                                 ("acquire_method", "show_method_col")):
            _action = QAction(tr(_label_key), w)
            _action.setCheckable(True)
            _action.setChecked(_key not in w.hidden_columns)
            _action.toggled.connect(
                lambda checked, k=_key: w.set_column_visible(k, checked))
            view_menu.addAction(_action)
            w._view_actions[_key] = _action

        # Справка
        help_menu = menubar.addMenu(tr("menu_help"))
        about_action = QAction(tr("menu_about"), w)
        about_action.setIcon(get_section_icon("about_tray", theme))
        about_action.setShortcut("F1")
        about_action.triggered.connect(lambda: self.show_dialog("about"))
        help_menu.addAction(about_action)
        changelog_action = QAction(tr("menu_changelog"), w)
        changelog_action.setIcon(get_section_icon("session", theme))
        changelog_action.setShortcut("F2")
        changelog_action.triggered.connect(lambda: self.show_dialog("changelog"))
        help_menu.addAction(changelog_action)
        docs_action = QAction(tr("menu_docs"), w)
        docs_action.setIcon(get_section_icon("games", theme))
        docs_action.setShortcut("F3")
        docs_action.triggered.connect(lambda: self.show_dialog("docs"))
        help_menu.addAction(docs_action)

    def rebuild_menu(self):
        """Перестраивает меню заново (для смены языка)."""
        self._w.menuBar().clear()
        self.build_menu()

    # ==================== ПРОВОДКА СЕКЦИЙ ====================

    def wire_sections(self):
        """Соединяет сигналы секций со слотами главного окна."""
        w = self._w
        w.auth_section.api_key_edit.textChanged.connect(w.on_api_key_changed)
        w.auth_section.eye_btn.toggled.connect(w.toggle_key_visibility)
        w.auth_section.check_api_btn.clicked.connect(w.check_api_key)
        w.auth_section.steam_id_edit.textChanged.connect(w.on_steam_id_changed)
        w.auth_section.check_steam_btn.clicked.connect(w.check_steam_id)
        w.profile_section.calc_btn.clicked.connect(w.calculate_playtime)
        w.table_section.rows_combo.currentTextChanged.connect(w.on_rows_per_page_changed)
        w.table_section.prev_btn.clicked.connect(w.prev_page)
        w.table_section.next_btn.clicked.connect(w.next_page)
        w.table_section.table.horizontalHeader().sectionClicked.connect(w.on_header_clicked)
        w.table_section.table.cellClicked.connect(w.on_cell_clicked)
        w.table_section.search_input.textChanged.connect(w.on_search_text_changed)

    # ==================== ФАБРИКИ CHROME ====================

    def make_language_button(self) -> QToolButton:
        """Кнопка-глобус: открывает список языков вверх (6 + прокрутка)."""
        btn = QToolButton()
        btn.setText("🌐")
        btn.setFixedSize(36, 30)
        btn.setToolTip(tr("change_language_tooltip"))
        btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 15px;
                padding: 0px;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        btn.clicked.connect(self._w.show_language_menu)
        self._language_btn = btn
        return btn

    def make_layout_toggle(self, dashboard) -> QToolButton:
        """Переключатель режима свободной сетки (замок открыт/закрыт)."""
        self._dashboard = dashboard
        btn = QToolButton()
        btn.setCheckable(True)
        btn.setChecked(dashboard.is_edit_mode())
        btn.setFixedSize(36, 30)
        btn.toggled.connect(self._on_layout_toggled)
        self._layout_btn = btn
        self.retranslate_chrome()
        return btn

    def _on_layout_toggled(self, checked: bool):
        if self._dashboard is not None:
            self._dashboard.set_edit_mode(checked)
        self.retranslate_chrome()

    def retranslate_chrome(self):
        """Обновляет тултипы chrome-элементов при смене языка/режима."""
        if self._language_btn is not None:
            self._language_btn.setToolTip(tr("change_language_tooltip"))
        if self._layout_btn is not None:
            editing = self._layout_btn.isChecked()
            self._layout_btn.setText("📐" if editing else "🔒")
            self._layout_btn.setToolTip(
                tr("layout_toggle_done") if editing else tr("layout_toggle_edit")
            )

    # ==================== ДИАЛОГИ ====================

    def show_dialog(self, kind: str):
        """Показывает диалог по имени из реестра DIALOGS."""
        func = DIALOGS.get(kind)
        if func is None:
            raise KeyError(f"Неизвестный диалог: {kind!r}")
        return func(self._w)

    # ==================== ШОРТКАТЫ ====================

    def init_shortcuts(self):
        """Инициализирует горячие клавиши окна."""
        return _init_shortcuts(self._w)

    # ==================== УРОВЕНЬ ПРИЛОЖЕНИЯ ====================

    @staticmethod
    def create_application(argv) -> QApplication:
        """Создаёт QApplication с базовыми настройками оболочки."""
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication(argv)
        app.setStyle(QStyleFactory.create("Fusion"))
        app.setFont(QFont("Segoe UI Semibold", 12))
        return app

    @staticmethod
    def ask_language() -> Optional[str]:
        """Диалог выбора языка. Возвращает имя языка или None (отмена)."""
        from PyQt5.QtWidgets import QDialog
        from ui.language_dialog import LanguageDialog
        dlg = LanguageDialog()
        if dlg.exec_() == QDialog.Accepted:
            return dlg.selected_language
        return None
