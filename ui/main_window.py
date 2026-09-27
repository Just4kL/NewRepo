# ui/main_window.py
"""Главное окно приложения Steam Playtime Viewer"""

import logging
import csv
import json
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTableWidgetItem, QMessageBox, QFileDialog, QApplication, QMenu
)
from PyQt5.QtCore import Qt, QTimer, QThread, QSettings, QPoint
from PyQt5.QtGui import QColor, QFont

from app.config import VERSION, BUILD_VERSION, AUTHOR, BUILD_DATE
from app.i18n import set_language, tr, get_translation, get_language_code
from app.steam_api import SteamAPIClient, SteamApiError
from app.cache import ProfileCache
from app.resources import get_app_icon

from ui.gui import Gui, DESIGN, SETTINGS_APP, SETTINGS_ORG
from ui.workers import AsyncWorker, ProgressBridge
from ui.widgets.auth_section import AuthSection
from ui.widgets.profile_section import ProfileSection
from ui.widgets.table_section import TableSection
from ui.widgets.dashboard import DashboardGrid
from ui.widgets.footer import FooterBar

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, language: str = 'Русский'):
        super().__init__()

        # Локализация
        self.language = language
        set_language(language)
        self.tr = get_translation()
        # RTL-раскладка для арабского, иначе LTR
        QApplication.instance().setLayoutDirection(
            Qt.RightToLeft if get_language_code() == "ar" else Qt.LeftToRight)

        # Данные
        self.api_key: str = ""
        self.steam_id: str = ""
        self.player_summary: Optional[Dict[str, Any]] = None
        self.games_data: List[Dict[str, Any]] = []
        self._all_games_data: List[Dict[str, Any]] = []

        # Пагинация и сортировка
        self.current_page: int = 0
        self.rows_per_page: int = 10
        self._sort_column: int = -1
        self._sort_reverse: bool = False

        # Группы серий: раскрытые ключи, знаменатель % (вся библиотека),
        # кэш entries текущей страницы
        self.expanded_groups: set = set()
        self.grand_total_min: int = 0
        self._entries: list = []

        # Видимость колонок таблицы (множество СКРЫТЫХ ключей TableSection)
        self.hidden_columns: set = set(TableSection.DEFAULT_HIDDEN)
        self._view_actions: dict = {}
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        # Статистика
        self.total_games: int = 0
        self.total_playtime_min: int = 0

        # UI
        self.is_key_visible: bool = False
        self.theme: str = "light"
        self.font_family: str = "Bahnschrift SemiBold"
        self.font_size: int = 14
        self.font_bold: bool = False
        self.font_italic: bool = False
        self.steam_url: str = ""

        # API
        self.api_client: Optional[SteamAPIClient] = None
        self.profile_cache = ProfileCache()

        # Асинхронность
        self._current_async_type: Optional[str] = None
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[AsyncWorker] = None
        self._progress_bridge: Optional[ProgressBridge] = None
        self.shortcuts = []

        # Константы для диалогов
        self.VERSION = VERSION
        self.BUILD_VERSION = BUILD_VERSION
        self.AUTHOR = AUTHOR
        self.BUILD_DATE = BUILD_DATE

        # Иконка окна
        self.setWindowIcon(get_app_icon())

        # Определяем разрешение экрана
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            self.screen_width = screen_geometry.width()
            self.screen_height = screen_geometry.height()
        else:
            self.screen_width = 1920
            self.screen_height = 1080

        # GUI-агрегатор: тема, стили, меню, диалоги, шорткаты, фабрики
        self.gui = Gui(self)

        # Настройка адаптивности
        self.setup_responsive_ui()

        # Заголовок окна
        self.setWindowTitle(f"{tr('app_title')} v{VERSION}")

        # Тема и стили (через агрегатор)
        self.apply_styles()

        # Инициализация UI
        self.init_ui()
        self.init_menu()
        self.shortcuts = self.gui.init_shortcuts()
        self.apply_font_settings()

        # Таймер автосохранения
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save_profile)

        # Таймер обновления статуса Steam (каждые 60 сек)
        self.status_refresh_timer = QTimer(self)
        self.status_refresh_timer.timeout.connect(self.refresh_user_status)
        self.status_refresh_timer.setInterval(60000)

        self._is_closing = False

    # ==================== АДАПТИВНОСТЬ ====================

    def setup_responsive_ui(self):
        """Адаптивная настройка размеров."""
        if self.screen_width <= 480:
            self.font_size = 8
        elif self.screen_width <= 800:
            self.font_size = 9
        elif self.screen_width <= 1366:
            self.font_size = 10
        elif self.screen_width >= 3840:
            self.font_size = 14
        else:
            self.font_size = 11

    # ==================== СТИЛИ ====================

    def apply_styles(self):
        """Применение стилей (делегировано GUI-агрегатору)."""
        self.gui.apply_theme(self.theme)

    def apply_font_settings(self):
        """Применение настроек шрифта (делегировано GUI-агрегатору)."""
        self.gui.apply_font_settings()

    # ==================== ШРИФТ ====================

    def increase_font_size(self):
        """Увеличение размера шрифта на 1 pt."""
        if self.font_size < 72:
            self.font_size += 1
            self.apply_font_settings()

    def decrease_font_size(self):
        """Уменьшение размера шрифта на 1 pt."""
        if self.font_size > 8:
            self.font_size -= 1
            self.apply_font_settings()

    def toggle_theme(self):
        """Переключение темы."""
        self.set_theme("dark" if self.theme == "light" else "light")

    def set_theme(self, theme: str):
        """Установка темы оформления."""
        self.theme = theme
        self.gui.apply_theme(theme)
        self.gui.apply_font_settings()
        self.profile_section.apply_theme(theme)
        if self.games_data:
            self.show_page()

    # ==================== ИНИЦИАЛИЗАЦИЯ UI ====================

    def init_ui(self):
        """Сборка окна: свободная сетка + нижняя панель.

        Растёт при растягивании окна только строка с таблицей —
        карточки аутентификации и профиля зафиксированы по высоте.
        """
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(DESIGN["spacing"])
        main_layout.setContentsMargins(*DESIGN["margins"])

        # Секции (ссылки остаются — вся логика ниже их использует)
        self.auth_section = AuthSection(self)
        self.profile_section = ProfileSection(self)
        self.table_section = TableSection(self)
        self.gui.wire_sections()

        # Подстановка сохранённых API-ключа и SteamID (перезаписываются
        # при каждом вводе в on_api_key_changed / on_steam_id_changed)
        self.auth_section.api_key_edit.setText(
            self._settings.value("auth/api_key", ""))
        self.auth_section.steam_id_edit.setText(
            self._settings.value("auth/steam_id", ""))

        # Восстановление видимости колонок
        saved_hidden = self._settings.value("table/hidden", None)
        if saved_hidden is not None:
            self.hidden_columns = set(saved_hidden)
        self.apply_column_visibility()

        # Свободная сетка: карточки можно двигать за ручку ⠿
        self.dashboard = DashboardGrid(self)
        self.dashboard.add_card("auth", self.auth_section)
        self.dashboard.add_card("profile", self.profile_section)
        self.dashboard.add_card("table", self.table_section, grow=True)
        main_layout.addWidget(self.dashboard, 1)

        # Нижняя панель: цитаты + замок сетки + язык
        self.footer = FooterBar(self)
        self.language_btn = self.gui.make_language_button()
        self.layout_btn = self.gui.make_layout_toggle(self.dashboard)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(6)
        bottom_layout.addWidget(self.footer, 1)
        bottom_layout.addWidget(self.layout_btn, 0, Qt.AlignVCenter)
        bottom_layout.addWidget(self.language_btn, 0, Qt.AlignVCenter)
        main_layout.addLayout(bottom_layout)

        # Разрешаем сжимать окно до минимума
        self.setMinimumSize(0, 0)
        # Стартовый размер: вписываемся в экран, а не фиксированные 1080x720
        self.resize(min(1080, max(640, self.screen_width - 80)),
                    min(720, max(480, self.screen_height - 60)))

    def init_menu(self):
        """Построение меню (делегировано GUI-агрегатору)."""
        self.gui.build_menu()

    # ==================== ГОРЯЧИЕ КЛАВИШИ ====================


    def focus_search(self):
        """Переводит фокус на поле поиска."""
        if self._all_games_data:
            self.table_section.search_input.setFocus()
            self.auth_section.status_label.setText(tr("search_focus_hint"))
        else:
            QMessageBox.information(self, tr("dlg_warning"), tr("no_data_search"))

    def manual_save_profile(self):
        """Ручное сохранение профиля."""
        if self.player_summary and self.games_data:
            self.auto_save_profile()
            QMessageBox.information(self, tr("dlg_success"), tr("success_profile_saved"))
        else:
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_no_data_export"))

    # ==================== ПЕРЕКЛЮЧЕНИЕ ЯЗЫКА ====================

    def toggle_language(self):
        """Переключение языка по порядку LANGUAGES (для тестов/API)."""
        from app.config import LANGUAGES
        names = [lang["name"] for lang in LANGUAGES]
        try:
            idx = names.index(self.language)
        except ValueError:
            idx = -1
        self._apply_language(names[(idx + 1) % len(names)])

    def _apply_language(self, name: str):
        """Применяет языковую модель: переводы, направление, весь UI."""
        self.language = name
        set_language(name)
        self.tr = get_translation()
        QApplication.instance().setLayoutDirection(
            Qt.RightToLeft if get_language_code() == "ar" else Qt.LeftToRight)

        self.retranslate_ui()
        self.setWindowTitle(f"{tr('app_title')} v{VERSION}")

    def _build_language_menu(self):
        """Меню выбора языка (без показа — для тестов)."""
        from app.config import LANGUAGES
        menu = QMenu(self)
        for lang in LANGUAGES:
            act = menu.addAction(f"{lang['flag']} {lang['native']}")
            act.setCheckable(True)
            act.setChecked(lang["name"] == self.language)
            act.setData(lang["name"])
            act.triggered.connect(
                lambda checked=False, n=lang["name"]: self._apply_language(n))
        # Видимо 6 пунктов, остальные — прокруткой (стрелки ▲▼)
        per_item = max(1, menu.sizeHint().height() // max(1, len(LANGUAGES)))
        menu.setMaximumHeight(per_item * 6 + 8)
        return menu

    def show_language_menu(self):
        """Список языков вверх от глобуса: 6 видно, остальные скроллом."""
        menu = self._build_language_menu()
        pos = self.language_btn.mapToGlobal(QPoint(0, 0))
        menu.exec_(QPoint(pos.x(), pos.y() - menu.sizeHint().height()))

    def retranslate_ui(self):
        """Обновление всех текстов интерфейса."""
        # Заголовки групп
        self.auth_section.setTitle(tr("auth_group"))
        self.profile_section.setTitle(tr("profile_group"))
        self.table_section.setTitle(tr("table_group"))

        # Поля ввода
        self.auth_section.api_key_edit.setPlaceholderText(tr("api_key_placeholder"))
        self.auth_section.steam_id_edit.setPlaceholderText(tr("steam_id_placeholder"))
        self.table_section.search_input.setPlaceholderText(tr("search_placeholder"))

        # Кнопки
        self.profile_section.calc_btn.setText(tr("calc_btn"))
        self.auth_section.get_key_btn.setText(tr("get_key_btn"))  # ← добавлено
        self.auth_section.get_key_btn.setToolTip(tr("get_key_btn_tooltip"))  # ← добавлено
        self.auth_section.get_id_btn.setText(tr("get_id_btn"))
        self.auth_section.check_api_btn.setText(tr("check_btn"))
        self.auth_section.check_steam_btn.setText(tr("check_btn"))

        # Тултипы
        self.auth_section.eye_btn.setToolTip(
            tr("eye_btn_tooltip_show") if self.is_key_visible else tr("eye_btn_tooltip_hide")
        )
        self.auth_section.check_api_btn.setToolTip(tr("check_btn_tooltip"))
        self.auth_section.check_steam_btn.setToolTip(tr("check_btn_tooltip"))
        self.auth_section.get_id_btn.setToolTip(tr("get_id_btn_tooltip"))

        # Заголовки таблицы
        headers = tr("table_headers")
        for i, header_text in enumerate(headers):
            item = self.table_section.table.horizontalHeaderItem(i)
            if item:
                item.setText(header_text)

        # Лейбл пагинации
        self.table_section.rows_label.setText(tr("rows_per_page"))
        # Комбо-бокс пагинации
        self.table_section.rows_combo.blockSignals(True)
        current_rows = self.rows_per_page
        self.table_section.rows_combo.clear()
        self.table_section.rows_combo.addItems(["10", "25", "50", "75", "100", tr("all")])
        if current_rows == "Все":
            self.table_section.rows_combo.setCurrentText(tr("all"))
        else:
            self.table_section.rows_combo.setCurrentText(str(current_rows))
        self.table_section.rows_combo.blockSignals(False)

        # Тултипы пагинации
        self.table_section.prev_btn.setToolTip(tr("prev_btn_tooltip"))
        self.table_section.next_btn.setToolTip(tr("next_btn_tooltip"))
        self.table_section.empty_label.setText(tr("table_empty_hint"))

        # Меню
        self.update_menu_texts()

        # Статусная строка (только один аргумент!)
        self.auth_section.status_label.setText(tr("ready"))
        self.gui.retranslate_chrome()
        self.dashboard.retranslate()

        # Итоговые метки
        self.update_summary_labels()
        self.update_page_label()

    def update_menu_texts(self):
        """Обновление текстов меню (делегировано GUI-агрегатору)."""
        self.gui.rebuild_menu()

    # ==================== ОБРАБОТЧИКИ ПОЛЕЙ ====================

    def on_api_key_changed(self, text: str):
        self.api_key = text
        # Сохраняем при каждом вводе: первое сохранение — при первом запуске,
        # дальше значение перезаписывается новым вводом.
        self._settings.setValue("auth/api_key", text)
        length = len(text)
        if length == 0:
            self.auth_section.api_key_edit.setStyleSheet("")
            self.auth_section.api_key_warning.setVisible(False)
        elif length == 32:
            self.auth_section.api_key_edit.setStyleSheet(
                f"background-color: #ccffcc; color: {'#000000' if self.theme == 'dark' else '#333333'};"
            )
            self.auth_section.api_key_warning.setVisible(False)
        else:
            self.auth_section.api_key_edit.setStyleSheet(
                f"background-color: #ffffcc; color: {'#000000' if self.theme == 'dark' else '#333333'};"
            )
            self.auth_section.api_key_warning.setText(tr("api_key_warning"))
            self.auth_section.api_key_warning.setVisible(True)

    def on_steam_id_changed(self, text: str):
        self.steam_id = text
        self._settings.setValue("auth/steam_id", text)
        length = len(text)
        if length == 0:
            self.auth_section.steam_id_edit.setStyleSheet("")
            self.auth_section.steam_id_warning.setVisible(False)
        elif length == 17 and text.isdigit():
            self.auth_section.steam_id_edit.setStyleSheet(
                f"background-color: #ccffcc; color: {'#000000' if self.theme == 'dark' else '#333333'};"
            )
            self.auth_section.steam_id_warning.setVisible(False)
        else:
            self.auth_section.steam_id_edit.setStyleSheet(
                f"background-color: #ffffcc; color: {'#000000' if self.theme == 'dark' else '#333333'};"
            )
            self.auth_section.steam_id_warning.setText(tr("steam_id_warning"))
            self.auth_section.steam_id_warning.setVisible(True)

    def toggle_key_visibility(self, checked: bool):
        self.is_key_visible = checked
        if checked:
            self.auth_section.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.auth_section.eye_btn.setText("🔓")
            self.auth_section.eye_btn.setStyleSheet(
                "background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;")
            self.auth_section.eye_btn.setToolTip(tr("eye_btn_tooltip_show"))
        else:
            self.auth_section.api_key_edit.setEchoMode(QLineEdit.Password)
            self.auth_section.eye_btn.setText("🔒")
            self.auth_section.eye_btn.setStyleSheet(
                "background-color: #d4edda; border: 1px solid #28a745; border-radius: 6px;")
            self.auth_section.eye_btn.setToolTip(tr("eye_btn_tooltip_hide"))

    # ==================== ПОИСК ====================

    def on_search_text_changed(self, text: str):
        if len(text) >= 14:
            self.table_section.search_warning.setText(tr("search_limit_warning"))
            self.table_section.search_warning.setVisible(True)
        else:
            self.table_section.search_warning.setVisible(False)

        if text.strip():
            filtered = [g for g in self._all_games_data if text.lower() in g["name"].lower()]
            if filtered:
                self.games_data = filtered
                self.table_section.search_input.setStyleSheet("")
                self.table_section.search_warning.setVisible(False)
            else:
                self.games_data = []
                self.table_section.search_input.setStyleSheet("background-color: #ffffcc; color: #333333;")
                self.table_section.search_warning.setText(tr("search_not_found"))
                self.table_section.search_warning.setVisible(True)
        else:
            self.games_data = self._all_games_data.copy()
            self.table_section.search_input.setStyleSheet("")
            self.table_section.search_warning.setVisible(False)
        self.current_page = 0
        self.show_page()

    # ==================== ПРОВЕРКИ ====================

    def check_api_key(self):
        key = self.auth_section.api_key_edit.text().strip()
        if len(key) != 32:
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_api_key_length"))
            return
        self.set_busy_state(True, tr("status_checking_api"))
        self.auth_section.check_api_btn.setEnabled(False)
        self.auth_section.check_api_btn.setText("⏳")
        self.api_client = SteamAPIClient(key)
        self._current_async_type = 'api_check'
        self.run_async(self.api_client.verify_api_key)

    def check_steam_id(self):
        steam_id = self.auth_section.steam_id_edit.text().strip()
        if len(steam_id) != 17 or not steam_id.isdigit():
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_steam_id_length"))
            return
        if not self.api_client:
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_check_api_first"))
            return
        self.set_busy_state(True, tr("status_checking_steam"))
        self.auth_section.check_steam_btn.setEnabled(False)
        self.auth_section.check_steam_btn.setText("⏳")
        self._current_async_type = 'steam_check'
        self.run_async(self.api_client.get_player_summaries, steam_id)

    # ==================== АСИНХРОННОСТЬ ====================

    def run_async(self, coro_func, *args, **kwargs):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker = AsyncWorker(coro_func, *args, **kwargs)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.finished.connect(self._on_async_finished)
        self.worker.error.connect(self._on_async_error)
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.start()

    def _on_async_finished(self, result):
        try:
            if self._current_async_type == 'api_check':
                self.on_api_check_finished(result)
            elif self._current_async_type == 'steam_check':
                self.on_steam_check_finished(result)
            elif self._current_async_type == 'games_load':
                self.on_games_loaded(result)
        finally:
            self.set_busy_state(False)
            self._cleanup_thread()

    def _on_async_error(self, error):
        logger.error("Async task error: %s", error)
        try:
            if self._current_async_type == 'api_check':
                self.on_api_check_error(error)
            elif self._current_async_type == 'steam_check':
                self.on_steam_check_error(error)
            elif self._current_async_type == 'games_load':
                self.on_games_error(error)
        finally:
            self.set_busy_state(False)
            self._cleanup_thread()

    def _cleanup_thread(self):
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None

    def set_busy_state(self, busy: bool, message: str = ""):
        if busy:
            for bar in (self.auth_section.progress,
                        self.profile_section.progress_bar):
                bar.setRange(0, 0)  # неопределённый режим, пока нет счётчиков
                bar.setVisible(True)
            self.auth_section.status_label.setText(message)
        else:
            self.auth_section.progress.setVisible(False)
            self.profile_section.progress_bar.setVisible(False)
            self.auth_section.status_label.setText(tr("ready"))

    def _on_load_progress(self, done: int, total: int):
        """Слот тиков загрузки: переключает бары в детерминированный режим."""
        for bar in (self.auth_section.progress,
                    self.profile_section.progress_bar):
            bar.setVisible(True)
            if total and total > 0:
                bar.setRange(0, total)
                bar.setValue(max(0, min(done, total)))
            else:
                bar.setRange(0, 0)

    # ==================== ОБРАБОТЧИКИ РЕЗУЛЬТАТОВ ====================

    @staticmethod
    def _describe_error(error) -> str:
        """Готовит текст ошибки для показа пользователю.

        SteamApiError уже содержит перевод — показываем его как есть.
        Для неожиданных исключений добавляем префикс контекста и
        техническую часть, чтобы она осталась в логе, а не в UI.
        """
        if isinstance(error, SteamApiError):
            return str(error)
        return str(error)

    def on_api_check_finished(self, result: bool):
        self.auth_section.check_api_btn.setEnabled(True)
        self.auth_section.check_api_btn.setText(tr("check_btn"))
        if result:
            QMessageBox.information(self, tr("dlg_success"), tr("success_api_valid"))
        else:
            QMessageBox.warning(self, tr("dlg_warning"), tr("success_api_invalid"))

    def on_api_check_error(self, error):
        self.auth_section.check_api_btn.setEnabled(True)
        self.auth_section.check_api_btn.setText(tr("check_btn"))
        QMessageBox.critical(self, tr("dlg_error"),
                             tr("error_check_api").format(self._describe_error(error)))

    def on_steam_check_finished(self, player_data: Dict[str, Any]):
        self.auth_section.check_steam_btn.setEnabled(True)
        self.auth_section.check_steam_btn.setText(tr("check_btn"))
        if not player_data:
            QMessageBox.warning(self, tr("dlg_warning"), tr("profile_load_error"))
            return
        self.player_summary = player_data
        self.update_user_status(player_data)
        self.profile_section.calc_btn.setEnabled(True)
        QMessageBox.information(self, tr("dlg_success"),
                                tr("success_profile_found").format(player_data.get("personaname", "")))

    def on_steam_check_error(self, error):
        self.auth_section.check_steam_btn.setEnabled(True)
        self.auth_section.check_steam_btn.setText(tr("check_btn"))
        self.profile_section.calc_btn.setEnabled(False)
        QMessageBox.critical(self, tr("dlg_error"),
                             tr("error_check_steam").format(self._describe_error(error)))

    def update_user_status(self, player_data: Dict[str, Any]):
        """Обновляет UI профиля на основе данных Steam."""
        game_info = player_data.get("gameextrainfo")
        if not player_data:
            return
        state = player_data.get("personastate", 0)
        status_map = {
            0: (tr("status_offline"), "#9e9e9e"),
            1: (tr("status_online"), "#4caf50"),
            2: (tr("status_busy"), "#ff9800"),
            3: (tr("status_away"), "#ff9800")
        }
        game_info = player_data.get("gameextrainfo")
        if game_info:
            status_text = tr("status_playing")
            color = "#2196f3"
        else:
            status_text, color = status_map.get(state, (tr("status_unknown"), "#9e9e9e"))
        nickname = player_data.get("personaname", tr("nickname_default"))
        steam_id = player_data.get("steamid", "")
        self.steam_url = f"https://steamcommunity.com/profiles/{steam_id}"
        self.profile_section.set_nickname(nickname, self.steam_url)
        self.profile_section.set_status(status_text, color, game_info if game_info else "")
        # Аватар: GetPlayerSummaries отдаёт avatar/avatarmedium/avatarfull.
        # Пустой URL — очистка (set_avatar сам создаёт QNAM лениво).
        self.profile_section.set_avatar(
            player_data.get("avatarmedium") or player_data.get("avatar") or "")

        # Запускаем таймер обновления статуса
        if not self.status_refresh_timer.isActive():
            self.status_refresh_timer.start()

    def refresh_user_status(self):
        """Обновляет статус Steam каждые 60 секунд."""
        if not self.api_client or not self.steam_id:
            return
        self.run_async(self._do_refresh_status)

    async def _do_refresh_status(self):
        """Асинхронное обновление статуса."""
        try:
            data = await self.api_client.get_player_summaries(self.steam_id)
            if data and 'players' in data and data['players']:
                self.player_summary = data['players'][0]
                self.update_user_status(self.player_summary)
        except Exception:
            pass  # Тихо игнорируем ошибки фонового обновления

    def on_steam_url_clicked(self, url: str):
        """Обработка клика по никнейму делегирована ProfileSection."""
        pass

    # ==================== ЗАГРУЗКА ИГР ====================

    def calculate_playtime(self):
        if not self.api_client:
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_api_not_initialized"))
            return
        if not self.steam_id:
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_steam_id_required"))
            return
        self.profile_section.calc_btn.setEnabled(False)
        self.profile_section.calc_btn.setText("⏳")
        self.set_busy_state(True, tr("status_loading_games"))
        self._current_async_type = 'games_load'
        # Мост прогресса: тики из воркера -> слот в GUI-потоке
        self._progress_bridge = ProgressBridge(self)
        self._progress_bridge.tick.connect(self._on_load_progress)
        self.run_async(self.api_client.get_all_games, self.steam_id,
                       progress_cb=self._progress_bridge.report)

    def on_games_loaded(self, games: List[Dict[str, Any]]):
        if games is None:
            self.profile_section.calc_btn.setEnabled(True)
            self.profile_section.calc_btn.setText(tr("calc_btn"))
            self.set_busy_state(False)
            return
        self.profile_section.calc_btn.setEnabled(True)
        self.profile_section.calc_btn.setText(tr("calc_btn"))
        self._all_games_data = games.copy()
        self.games_data = games
        self.total_games = len(games)
        self.total_playtime_min = sum(g["playtime_forever"] for g in games)
        # Знаменатель % — вся библиотека; поиск его не меняет, доли стабильны
        self.grand_total_min = self.total_playtime_min
        for g in games:
            g["share"] = round(g["playtime_forever"] / self.grand_total_min * 100, 2) \
                if self.grand_total_min else 0.0
        self.games_data.sort(key=lambda x: x["playtime_forever"], reverse=True)
        self._sort_column = -1
        self._sort_reverse = False
        self.expanded_groups = set()
        self.update_summary_labels()
        self.current_page = 0
        self.show_page()
        self.auto_save_timer.start(3000)
        self.set_busy_state(False)

    def on_games_error(self, error):
        self.profile_section.calc_btn.setEnabled(True)
        self.profile_section.calc_btn.setText(tr("calc_btn"))
        QMessageBox.critical(self, tr("dlg_error"),
                             tr("error_load_games").format(self._describe_error(error)))

    def update_summary_labels(self):
        total_hours = round(self.total_playtime_min / 60, 2)
        hours_int = int(total_hours)
        mins_int = int(self.total_playtime_min)
        self.profile_section.set_total_time(str(hours_int), str(mins_int))
        self.table_section.total_games_label.setText(
            tr("games_found").format(self.total_games)
        )

    # ==================== ТАБЛИЦА (группы серий + %) ====================

    def _rebuild_entries(self):
        """Строит entries из games_data и сортирует их текущим ключом.

        entries: [{"kind": "game", "game": g}] или
                 [{"kind": "group", "key": base, "agg": {...}, "members": [...]}].
        Инвариант: после сборки games_data переписывается в порядке показа
        (группы — подряд своими детьми). Поэтому плоские накопительные
        всегда совпадают с отображаемыми, сортировка и экспорт стабильны.
        """
        from app.grouping import group_games
        raw = group_games(self.games_data)
        entries = []
        for item in raw:
            if item["kind"] == "game":
                entries.append(item)
            else:
                key = item["agg"]["name"].lower()
                entries.append({"kind": "group", "key": key,
                                "agg": item["agg"], "members": item["members"]})
        # Свежие значения для сортировки: свежие агрегаты без cum = 0.0,
        # что ломало бы сортировку по Σ (группы вставали бы первыми)
        self._ensure_cumulative()
        self._annotate_aggs(entries)
        if self._sort_column == -1:
            entries.sort(key=lambda e: self._payload(e)["playtime_forever"],
                         reverse=True)
        elif self._sort_column == 5:
            # Σ порядко-зависима: плоский список уже отсортирован вызовом,
            # entries идут в его first-seen порядке без пересортировки
            pass
        else:
            key = self._sort_key(self._sort_column)
            entries.sort(key=lambda e: key(self._payload(e)),
                         reverse=self._sort_reverse)
        # Коммитим порядок показа обратно в плоский список
        self.games_data = [
            g for e in entries
            for g in ((e["game"],) if e["kind"] == "game" else e["members"])
        ]
        # Свежая аннотация в финальном порядке + агрегаты групп
        self._ensure_cumulative()
        self._annotate_aggs(entries)
        self._entries = entries

    def _annotate_aggs(self, entries):
        """Проставляет агрегатам cum = max детей (сортировка и рендер)."""
        for e in entries:
            if e["kind"] == "group":
                members = e["members"]
                e["agg"]["cum_h"] = max(m.get("cum_h", 0.0) for m in members)
                e["agg"]["cum_p"] = max(m.get("cum_p", 0.0) for m in members)

    @staticmethod
    def _payload(entry):
        """Словарь-строка для сортировки: игра или агрегат группы."""
        return entry["game"] if entry["kind"] == "game" else entry["agg"]

    def _ensure_cumulative(self):
        """Аннотирует games_data накопительными (cum_h, cum_p) в плоском порядке.

        Вызывается только из _rebuild_entries после коммита порядка показа,
        поэтому значения всегда соответствуют отображению. Последний —
        ровно 100.0 (итог пирога всегда 100%).
        """
        run_h = 0.0
        run_p = 0.0
        for g in self.games_data:
            run_h += g.get("playtime_forever", 0) / 60
            run_p += g.get("share", 0.0)
            g["cum_h"] = round(run_h, 2)
            g["cum_p"] = round(run_p, 1)
        if self.games_data:
            self.games_data[-1]["cum_p"] = 100.0

    @staticmethod
    def _sort_key(logicalIndex: int):
        sort_keys = {
            0: lambda x: x.get("appid", 0),
            1: lambda x: x["name"].lower(),
            2: lambda x: float(x["hours"]),
            3: lambda x: float(x["minutes"]),
            4: lambda x: float(x.get("share", 0.0)),
            5: lambda x: float(x.get("cum_h", 0.0)),
            6: lambda x: x["acquired"],
            7: lambda x: int(x["achievements"]["unlocked"]),
            8: lambda x: x["last_played"],
            9: lambda x: x["acquire_method"],
        }
        return sort_keys.get(logicalIndex, lambda x: x["name"].lower())

    def _flat_rows(self):
        """Плоский список (entry, child|None) с учётом раскрытия групп."""
        flat = []
        for entry in self._entries:
            flat.append((entry, None))
            if entry["kind"] == "group" and entry["key"] in self.expanded_groups:
                for game in entry["members"]:
                    flat.append((entry, game))
        return flat

    def show_page(self):
        if not self.games_data:
            self._entries = []
            self.table_section.table.setRowCount(0)
            self.table_section.update_empty_state()
            return
        self._rebuild_entries()
        flat = self._flat_rows()
        total_rows = len(flat)
        if self.rows_per_page == "Все":
            rows_to_show = total_rows
            total_pages = 1
        else:
            rows_to_show = int(self.rows_per_page)
            total_pages = max(1, (total_rows + rows_to_show - 1) // rows_to_show)
        self.current_page = max(0, min(self.current_page, total_pages - 1))
        start_idx = self.current_page * rows_to_show
        end_idx = min(start_idx + rows_to_show, total_rows)
        table = self.table_section.table
        table.setRowCount(end_idx - start_idx)
        bold = QFont()
        bold.setBold(True)
        for i, (entry, child) in enumerate(flat[start_idx:end_idx]):
            if child is None and entry["kind"] == "group":
                self._render_group_row(table, i, entry, start_idx + i, bold)
            else:
                game = child if child is not None else entry["game"]
                self._render_game_row(table, i, game, start_idx + i,
                                      indent=child is not None)
        self.update_page_label()
        self.table_section.update_empty_state()
        self.table_section.prev_btn.setEnabled(self.current_page > 0)
        self.table_section.next_btn.setEnabled(self.current_page < total_pages - 1)

    @staticmethod
    def _cum_text(cum_h: float, cum_p: float) -> str:
        """Текст накопительной ячейки: часы · процент."""
        return f"{cum_h:.2f} · {cum_p:.1f}%".replace('.', ',')

    def _render_game_row(self, table, i: int, game: Dict[str, Any],
                         global_idx: int, indent: bool = False):
        """Строка одной игры (или ребёнка группы с отступом)."""
        row_num = global_idx + 1
        num_item = QTableWidgetItem(str(row_num))
        num_item.setTextAlignment(Qt.AlignCenter)
        name_item = QTableWidgetItem(("↳ " if indent else "") + game["name"])
        name_item.setToolTip(game["name"])
        hours_item = QTableWidgetItem()
        hours_item.setData(Qt.DisplayRole, float(game["hours"]))
        hours_item.setText(f"{game['hours']:.2f}".replace('.', ','))
        hours_item.setTextAlignment(Qt.AlignCenter)
        mins_item = QTableWidgetItem()
        mins_item.setData(Qt.DisplayRole, float(game["minutes"]))
        mins_item.setText(f"{game['minutes']:.2f}".replace('.', ','))
        mins_item.setTextAlignment(Qt.AlignCenter)
        share_item = QTableWidgetItem()
        share_item.setData(Qt.DisplayRole, float(game.get("share", 0.0)))
        share_item.setText(f"{game.get('share', 0.0):.1f}".replace('.', ',') + "%")
        share_item.setTextAlignment(Qt.AlignCenter)
        cum_item = QTableWidgetItem()
        cum_item.setData(Qt.DisplayRole, float(game.get("cum_h", 0.0)))
        cum_item.setText(self._cum_text(float(game.get("cum_h", 0.0)),
                                        float(game.get("cum_p", 0.0))))
        cum_item.setTextAlignment(Qt.AlignCenter)
        acquired_item = QTableWidgetItem(game["acquired"])
        acquired_item.setTextAlignment(Qt.AlignCenter)
        ach = game["achievements"]
        ach_item = QTableWidgetItem(
            tr("achievements_format").format(ach["unlocked"], ach["total"]))
        ach_item.setTextAlignment(Qt.AlignCenter)
        if ach['unlocked'] == ach['total'] and ach['total'] > 0:
            ach_item.setBackground(QColor("#ccffcc"))
        last_played_item = QTableWidgetItem(game["last_played"])
        last_played_item.setTextAlignment(Qt.AlignCenter)
        method_item = QTableWidgetItem(game["acquire_method"])
        method_item.setTextAlignment(Qt.AlignCenter)
        items = [num_item, name_item, hours_item, mins_item, share_item,
                 cum_item, acquired_item, ach_item, last_played_item, method_item]
        for col, item in enumerate(items):
            table.setItem(i, col, item)
        self._paint_row_bg(table, i, global_idx)

    def _render_group_row(self, table, i: int, entry: Dict[str, Any],
                          global_idx: int, bold: QFont):
        """Строка группы: агрегаты + раскрывалка в колонке №."""
        agg = entry["agg"]
        n = len(entry["members"])
        expanded = entry["key"] in self.expanded_groups
        num_item = QTableWidgetItem("▼" if expanded else "▶")
        num_item.setTextAlignment(Qt.AlignCenter)
        num_item.setFont(bold)
        name_item = QTableWidgetItem(f"{agg['name']} ({n})")
        name_item.setToolTip(f"{agg['name']} — {n}")
        name_item.setFont(bold)
        hours_item = QTableWidgetItem(f"{agg['hours']:.2f}".replace('.', ','))
        hours_item.setTextAlignment(Qt.AlignCenter)
        hours_item.setFont(bold)
        mins_item = QTableWidgetItem(f"{agg['minutes']:.2f}".replace('.', ','))
        mins_item.setTextAlignment(Qt.AlignCenter)
        mins_item.setFont(bold)
        share_item = QTableWidgetItem(
            f"{agg.get('share', 0.0):.1f}".replace('.', ',') + "%")
        share_item.setTextAlignment(Qt.AlignCenter)
        share_item.setFont(bold)
        cum_item = QTableWidgetItem(
            self._cum_text(float(agg.get("cum_h", 0.0)),
                           float(agg.get("cum_p", 0.0))))
        cum_item.setTextAlignment(Qt.AlignCenter)
        cum_item.setFont(bold)
        acquired_item = QTableWidgetItem(agg["acquired"])
        acquired_item.setTextAlignment(Qt.AlignCenter)
        ach = agg["achievements"]
        ach_item = QTableWidgetItem(
            tr("achievements_format").format(ach["unlocked"], ach["total"]))
        ach_item.setTextAlignment(Qt.AlignCenter)
        last_played_item = QTableWidgetItem(agg["last_played"])
        last_played_item.setTextAlignment(Qt.AlignCenter)
        method_item = QTableWidgetItem(agg["acquire_method"])
        method_item.setTextAlignment(Qt.AlignCenter)
        items = [num_item, name_item, hours_item, mins_item, share_item,
                 cum_item, acquired_item, ach_item, last_played_item, method_item]
        for col, item in enumerate(items):
            table.setItem(i, col, item)
        self._paint_row_bg(table, i, global_idx)

    def _paint_row_bg(self, table, i: int, global_idx: int):
        """Подсветка топ-10/топ-20 по плоскому индексу."""
        if global_idx < 10:
            bg = QColor("#4a4a00") if self.theme == "dark" else QColor("#e0ffe0")
        elif global_idx < 20:
            bg = QColor("#4a004a") if self.theme == "dark" else QColor("#ffffe0")
        else:
            bg = None
        if bg:
            for col in range(table.columnCount()):
                item = table.item(i, col)
                if item:
                    item.setBackground(bg)

    def on_header_clicked(self, logicalIndex: int):
        key = self._sort_key(logicalIndex)
        if self._sort_column == logicalIndex:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = logicalIndex
            self._sort_reverse = False
        # games_data всегда в порядке показа с актуальными cum
        # (инвариант _rebuild_entries), поэтому сортировка корректна,
        # включая Σ (монотонный ключ: keep/reverse).
        # Дети групп наследуют порядок плоского списка (и порядок экспорта)
        self.games_data.sort(key=key, reverse=self._sort_reverse)
        self.current_page = 0
        self.show_page()

    def on_cell_clicked(self, row: int, col: int):
        """Клик по ▼/▶ в колонке № раскрывает/сворачивает группу."""
        table = self.table_section.table
        if col != 0 or not (0 <= row < table.rowCount()):
            return
        flat = self._flat_rows()
        rows_to_show = len(flat) if self.rows_per_page == "Все" else int(self.rows_per_page)
        start_idx = self.current_page * rows_to_show
        if not (0 <= start_idx + row < len(flat)):
            return
        entry, child = flat[start_idx + row]
        if entry["kind"] == "group" and child is None:
            if entry["key"] in self.expanded_groups:
                self.expanded_groups.discard(entry["key"])
            else:
                self.expanded_groups.add(entry["key"])
            self.show_page()

    def on_rows_per_page_changed(self, text: str):
        if not text:
            return
        self.rows_per_page = "Все" if text == "Все" or text == tr("all") else int(text)
        self.current_page = 0
        self.show_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_page()

    def next_page(self):
        if self.current_page < self.get_total_pages() - 1:
            self.current_page += 1
            self.show_page()

    def get_total_pages(self) -> int:
        total = len(self._flat_rows())
        if not total:
            return 1
        if self.rows_per_page == "Все":
            return 1
        rows = int(self.rows_per_page)
        return (total + rows - 1) // rows

    def update_page_label(self):
        total_pages = self.get_total_pages()
        self.table_section.page_label.setText(
            tr("page_label").format(self.current_page + 1, total_pages)
        )

    # ==================== ВИДИМОСТЬ КОЛОНОК ====================

    def apply_column_visibility(self):
        """Применяет hidden_columns к таблице."""
        for key in TableSection.COLUMN_KEYS:
            self.table_section.set_column_visible(
                key, key not in self.hidden_columns)

    def set_column_visible(self, key: str, visible: bool):
        """Переключает колонку из меню «Вид» и запоминает выбор."""
        if visible:
            self.hidden_columns.discard(key)
        else:
            self.hidden_columns.add(key)
        self.table_section.set_column_visible(key, visible)
        self._settings.setValue("table/hidden", sorted(self.hidden_columns))
        # Синхронизируем галочку меню (без рекурсии в toggled)
        act = self._view_actions.get(key)
        if act is not None and act.isChecked() != visible:
            act.blockSignals(True)
            act.setChecked(visible)
            act.blockSignals(False)

    @staticmethod
    def _cell_text(key: str, game: Dict[str, Any], idx: int, numeric: bool = False):
        """Текстовое (или числовое для XLSX) значение ячейки по ключу колонки."""
        if key == "num":
            return idx
        if key == "name":
            return game["name"]
        if key == "hours":
            return float(game["hours"]) if numeric else f"{game['hours']:.2f}".replace('.', ',')
        if key == "minutes":
            return float(game["minutes"]) if numeric else f"{game['minutes']:.2f}".replace('.', ',')
        if key == "share":
            share = float(game.get("share", 0.0))
            return share if numeric else f"{share:.1f}".replace('.', ',') + "%"
        if key == "cumulative":
            ch = float(game.get("cum_h", 0.0))
            cp = float(game.get("cum_p", 0.0))
            return ch if numeric else MainWindow._cum_text(ch, cp)
        if key == "acquired":
            return game["acquired"]
        if key == "achievements":
            ach = game["achievements"]
            return tr("achievements_format").format(ach["unlocked"], ach["total"])
        if key == "last_played":
            return game["last_played"]
        if key == "acquire_method":
            return game["acquire_method"]
        return ""

    def _export_table(self, numeric: bool = False):
        """Заголовки и строки только видимых колонок.

        Накопительные берутся из последнего показа (порядок отображения),
        чтобы совпадать с таблицей; запасной путь — плоский расчёт.
        """
        if any("cum_h" not in g for g in self.games_data):
            self._ensure_cumulative()
        headers_all = tr("table_headers")
        cols = [(i, k) for i, k in enumerate(TableSection.COLUMN_KEYS)
                if k not in self.hidden_columns]
        headers = [headers_all[i] for i, _ in cols]
        rows = [[self._cell_text(k, game, idx, numeric)
                 for _, k in cols]
                for idx, game in enumerate(self.games_data, 1)]
        return headers, rows

    # ==================== ФАЙЛОВЫЕ ОПЕРАЦИИ ====================

    def open_profile(self):
        filepath, _ = QFileDialog.getOpenFileName(self, tr("menu_open"), "", "JSON Files (*.json)")
        if not filepath:
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "steam_id" in data:
                self.auth_section.steam_id_edit.setText(data["steam_id"])
            if "api_key" in data:
                self.auth_section.api_key_edit.setText(data["api_key"])
            QMessageBox.information(self, tr("dlg_success"), tr("success_profile_loaded"))
        except Exception as e:
            QMessageBox.critical(self, tr("dlg_error"), tr("error_open_profile").format(str(e)))

    def export_csv(self):
        if not self.games_data:
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_no_data_export"))
            return
        filepath, _ = QFileDialog.getSaveFileName(self, tr("menu_export_csv"), "", "CSV Files (*.csv)")
        if not filepath:
            return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                headers, rows = self._export_table(numeric=False)
                writer.writerow(headers)
                writer.writerows(rows)
            QMessageBox.information(self, tr("dlg_success"), tr("success_exported").format(filepath))
        except Exception as e:
            QMessageBox.critical(self, tr("dlg_error"), tr("error_export").format(str(e)))

    def export_xlsx(self):
        if not self.games_data:
            QMessageBox.warning(self, tr("dlg_warning"), tr("error_no_data_export"))
            return
        try:
            import openpyxl
        except ImportError:
            QMessageBox.critical(self, tr("dlg_error"), "openpyxl not installed")
            return
        filepath, _ = QFileDialog.getSaveFileName(self, tr("menu_export_xlsx"), "", "Excel Files (*.xlsx)")
        if not filepath:
            return
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            headers, rows = self._export_table(numeric=True)
            ws.append(headers)
            for row in rows:
                ws.append(row)
            wb.save(filepath)
            QMessageBox.information(self, tr("dlg_success"), tr("success_exported").format(filepath))
        except Exception as e:
            QMessageBox.critical(self, tr("dlg_error"), tr("error_export").format(str(e)))

    # ==================== АВТОСОХРАНЕНИЕ ====================

    def auto_save_profile(self):
        if self.player_summary and self.games_data:
            try:
                self.profile_cache.save(self.steam_id, self.player_summary, self.games_data)
                self.auth_section.status_label.setText(tr("success_profile_saved"))
            except Exception as e:
                logger.error(f"Ошибка автосохранения: {e}")

    def closeEvent(self, event):
        self._is_closing = True
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
        logger.info("Программа закрыта.")
        super().closeEvent(event)
