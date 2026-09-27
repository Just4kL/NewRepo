# ui/widgets/table_section.py
"""Секция таблицы с корректным изменением ширины колонок"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QHeaderView, QStackedWidget, QWidget,
    QAbstractItemView, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QFont, QRegExpValidator

from app.i18n import tr


class TableSection(QGroupBox):
    """Секция таблицы."""

    # Порядок колонок = порядок заголовков tr("table_headers").
    # Индексы стабильны: скрытие идёт через setColumnHidden, поэтому
    # сортировка и экспорт не ломаются.
    COLUMN_KEYS = ("num", "name", "hours", "minutes", "share", "cumulative",
                   "acquired", "achievements", "last_played", "acquire_method")
    COLUMN_INDEX = {key: i for i, key in enumerate(COLUMN_KEYS)}
    # По умолчанию скрыты: дата получения (API её не отдаёт — всегда "?")
    # и способ получения (пока заглушка "?").
    DEFAULT_HIDDEN = frozenset(("acquired", "acquire_method"))

    def __init__(self, parent=None):
        super().__init__(tr("table_group"), parent)
        self.parent = parent
        self.init_ui()

    def set_column_visible(self, key: str, visible: bool):
        """Показывает/скрывает колонку, не трогая индексы и данные."""
        self.table.setColumnHidden(self.COLUMN_INDEX[key], not visible)

    def is_column_visible(self, key: str) -> bool:
        return not self.table.isColumnHidden(self.COLUMN_INDEX[key])

    def visible_columns(self):
        """Список (index, key) видимых колонок по порядку."""
        return [(i, k) for i, k in enumerate(self.COLUMN_KEYS)
                if self.is_column_visible(k)]

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        # ===== ПОИСК =====
        search_layout = QHBoxLayout()
        search_layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search_placeholder"))
        self.search_input.setMaxLength(14)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(26)
        self.search_input.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.search_input.setFixedWidth(250)

        validator = QRegExpValidator(QRegExp("[A-Za-z0-9А-Яа-яЁё\\s]{0,14}"))
        self.search_input.setValidator(validator)

        search_layout.addWidget(self.search_input)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        self.search_warning = QLabel("")
        self.search_warning.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.search_warning.setAlignment(Qt.AlignCenter)
        self.search_warning.setVisible(False)
        self.search_warning.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.search_warning)

        # ===== ТАБЛИЦА =====
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(tr("table_headers"))

        # ===== НАСТРОЙКА ЗАГОЛОВКА =====
        header = self.table.horizontalHeader()

        # ВАЖНО: Используем Interactive для ВСЕХ колонок
        # Без Stretch - колонки не будут автоматически растягиваться
        header.setSectionResizeMode(QHeaderView.Interactive)

        # Устанавливаем начальные ширины
        self.table.setColumnWidth(0, 54)  # № (+запас под "Nr./No./Č.")
        self.table.setColumnWidth(1, 250)  # Название игры
        self.table.setColumnWidth(2, 100)  # Время (ч)
        self.table.setColumnWidth(3, 100)  # Время (м)
        self.table.setColumnWidth(4, 64)  # Доля %
        self.table.setColumnWidth(5, 120)  # Σ время (накопительно)
        self.table.setColumnWidth(6, 120)  # Дата получения
        self.table.setColumnWidth(7, 120)  # Достижения
        self.table.setColumnWidth(8, 150)  # Время последнего запуска
        self.table.setColumnWidth(9, 130)  # Способ получения

        # Отключаем растягивание последней колонки
        header.setStretchLastSection(True)

        # Минимальная ширина секций
        header.setMinimumSectionSize(8)

        # ===== НАСТРОЙКА ТАБЛИЦЫ =====
        self.table.setSortingEnabled(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)

        # Адаптивная высота строк
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.verticalHeader().setMinimumSectionSize(8)

        # Таблица растягивается
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Стиль заголовка
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #4a4a4a;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: 1px solid #666666;
            }
            QHeaderView::section:hover {
                background-color: #5a5a5a;
            }
        """)

        # ===== ТАБЛИЦА / EMPTY-STATE (стопка: данные или подсказка) =====
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)

        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setContentsMargins(12, 12, 12, 12)
        empty_layout.addStretch(1)
        empty_icon = QLabel("🎮")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setFont(QFont("Segoe UI Emoji", 40))
        empty_layout.addWidget(empty_icon)
        self.empty_label = QLabel(tr("table_empty_hint"))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        empty_layout.addWidget(self.empty_label)
        empty_layout.addStretch(1)
        self.stack.addWidget(empty_page)
        self.stack.setCurrentIndex(1)

        layout.addWidget(self.stack, stretch=1)

        # ===== ПАГИНАЦИЯ =====
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)

        self.rows_label = QLabel(tr("rows_per_page"))
        pagination_layout.addWidget(self.rows_label)

        self.rows_combo = QComboBox()
        self.rows_combo.addItems(["10", "25", "50", "75", "100", tr("all")])
        self.rows_combo.setFixedWidth(70)
        self.rows_combo.setMinimumHeight(8)
        pagination_layout.addWidget(self.rows_combo)

        pagination_layout.addStretch()

        # Кнопка предыдущей страницы
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(64, 32)
        self.prev_btn.setToolTip(tr("prev_btn_tooltip"))
        pagination_layout.addWidget(self.prev_btn)

        self.page_label = QLabel(tr("page_label").format(1, 1))
        self.page_label.setStyleSheet("font-weight: bold; padding: 0 5px;")
        self.page_label.setAlignment(Qt.AlignCenter)
        pagination_layout.addWidget(self.page_label)

        # Кнопка следующей страницы
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(64, 32)
        self.next_btn.setToolTip(tr("next_btn_tooltip"))
        pagination_layout.addWidget(self.next_btn)

        layout.addLayout(pagination_layout)

        # ===== ИТОГИ =====
        summary_layout = QHBoxLayout()
        self.total_games_label = QLabel(tr("total_games").format(0))
        self.total_games_label.setStyleSheet("font-weight: bold;")
        self.total_games_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        summary_layout.addWidget(self.total_games_label)
        summary_layout.addStretch()
        layout.addLayout(summary_layout)

        # Колонки-заглушки скрыты, пока пользователь не включит их в меню «Вид»
        for _key in self.DEFAULT_HIDDEN:
            self.set_column_visible(_key, False)

    def update_empty_state(self):
        """Переключает таблицу и заглушку в зависимости от наличия строк."""
        self.stack.setCurrentIndex(0 if self.table.rowCount() else 1)