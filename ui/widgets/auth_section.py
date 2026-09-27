# ui/widgets/auth_section.py
"""Секция аутентификации с адаптивной вёрсткой"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QProgressBar
)
from PyQt5.QtCore import QUrl, Qt, QRegExp
from PyQt5.QtGui import QDesktopServices, QFont, QRegExpValidator

from app.config import STEAM_API_KEY_URL, STEAM_ID_URL
from app.i18n import tr


class AuthSection(QGroupBox):
    """Секция аутентификации Steam."""

    def __init__(self, parent=None):
        super().__init__(tr("auth_group"), parent)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        # Карточка по контенту: рост окна ей не достаётся
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        # ===== API KEY =====
        api_grid = QGridLayout()
        api_grid.setColumnStretch(0, 0)
        api_grid.setColumnStretch(1, 1)
        api_grid.setColumnStretch(2, 0)
        api_grid.setSpacing(6)

        api_label = QLabel(tr("api_key_label"))
        api_label.setMinimumWidth(90)
        api_label.setWordWrap(True)
        api_grid.addWidget(api_label, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText(tr("api_key_placeholder"))
        self.api_key_edit.setMinimumHeight(14)
        self.api_key_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        api_validator = QRegExpValidator(QRegExp("[A-Fa-f0-9]{0,32}"))
        self.api_key_edit.setValidator(api_validator)
        api_grid.addWidget(self.api_key_edit, 0, 1)

        api_buttons = QHBoxLayout()
        api_buttons.setSpacing(4)

        self.eye_btn = QPushButton("🔒")
        self.eye_btn.setCheckable(True)
        self.eye_btn.setFont(QFont("Segoe UI Emoji", 14))
        self.eye_btn.setFixedHeight(28)
        self.eye_btn.setToolTip(tr("eye_btn_tooltip_hide"))
        api_buttons.addWidget(self.eye_btn)

        self.get_key_btn = QPushButton(tr("get_key_btn"))
        self.get_key_btn.setFont(QFont("Segoe UI Emoji", 12))
        self.get_key_btn.setFixedHeight(28)
        self.get_key_btn.setToolTip(tr("get_key_btn_tooltip"))
        self.get_key_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(STEAM_API_KEY_URL))
        )
        api_buttons.addWidget(self.get_key_btn)

        self.check_api_btn = QPushButton(tr("check_btn"))
        self.check_api_btn.setObjectName("primary")
        self.check_api_btn.setFont(QFont("Segoe UI Emoji", 12))
        self.check_api_btn.setFixedHeight(28)
        self.check_api_btn.setToolTip(tr("check_btn_tooltip"))
        api_buttons.addWidget(self.check_api_btn)

        api_grid.addLayout(api_buttons, 0, 2)
        layout.addLayout(api_grid)

        self.api_key_warning = QLabel("")
        self.api_key_warning.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.api_key_warning.setVisible(False)
        self.api_key_warning.setWordWrap(True)
        layout.addWidget(self.api_key_warning)

        # ===== STEAM ID =====
        steam_grid = QGridLayout()
        steam_grid.setColumnStretch(0, 0)
        steam_grid.setColumnStretch(1, 1)
        steam_grid.setColumnStretch(2, 0)
        steam_grid.setSpacing(6)

        steam_label = QLabel(tr("steam_id_label"))
        steam_label.setMinimumWidth(90)
        steam_label.setWordWrap(True)
        steam_grid.addWidget(steam_label, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)

        self.steam_id_edit = QLineEdit()
        self.steam_id_edit.setPlaceholderText(tr("steam_id_placeholder"))
        self.steam_id_edit.setMinimumHeight(14)
        self.steam_id_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        steam_validator = QRegExpValidator(QRegExp("[0-9]{0,17}"))
        self.steam_id_edit.setValidator(steam_validator)
        steam_grid.addWidget(self.steam_id_edit, 0, 1)

        # Кнопки Steam ID (получить + проверить)
        steam_buttons = QHBoxLayout()
        steam_buttons.setSpacing(4)

        self.get_id_btn = QPushButton(tr("get_id_btn"))
        self.get_id_btn.setObjectName("secondary")
        self.get_id_btn.setFixedHeight(28)
        self.get_id_btn.setToolTip(tr("get_id_btn_tooltip"))
        self.get_id_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(STEAM_ID_URL))
        )
        steam_buttons.addWidget(self.get_id_btn)

        self.check_steam_btn = QPushButton(tr("check_btn"))
        self.check_steam_btn.setObjectName("primary")
        self.check_steam_btn.setFont(QFont("Segoe UI Emoji", 12))
        self.check_steam_btn.setFixedHeight(28)
        self.check_steam_btn.setToolTip(tr("check_btn_tooltip"))
        steam_buttons.addWidget(self.check_steam_btn)

        steam_grid.addLayout(steam_buttons, 0, 2)

        layout.addLayout(steam_grid)

        self.steam_id_warning = QLabel("")
        self.steam_id_warning.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.steam_id_warning.setVisible(False)
        self.steam_id_warning.setWordWrap(True)
        layout.addWidget(self.steam_id_warning)

        # Прогресс-бар (скрыт по умолчанию)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimumHeight(16)
        self.progress.setMaximumHeight(20)
        self.progress.setTextVisible(True)
        self.progress.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress)

        # Статусная строка
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: blue;")
        layout.addWidget(self.status_label)