# ui/widgets/profile_section.py
"""Секция профиля — компактная карточка с аватаром"""

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QProgressBar, QDialog, QSizePolicy
)
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtGui import QFont, QCursor, QPixmap, QDesktopServices
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

from app.i18n import tr
from app.resources import get_section_icon


_LAYOUT_TOKENS = None


def _layout_tokens():
    """Токены лейаута из tokens/layout.json — в коде магических чисел нет."""
    global _LAYOUT_TOKENS
    if _LAYOUT_TOKENS is None:
        import json
        import os
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(root, "tokens", "layout.json"), encoding="utf-8") as fh:
            _LAYOUT_TOKENS = json.load(fh)
    return _LAYOUT_TOKENS


class ProfileSection(QGroupBox):
    """Секция профиля пользователя с аватаром и статусом."""

    def __init__(self, parent=None):
        super().__init__(tr("profile_group"), parent)
        self.parent = parent
        self.steam_url = ""
        self.theme = "light"
        self._avatar_url = ""
        self.init_ui()

    def init_ui(self):
        from ui.gui import DESIGN

        # Потолок на случай огромных шрифтов; точную высоту задаёт
        # MainWindow._sync_card_heights (вровень с аутентификацией)
        self.setMaximumHeight(DESIGN["profile_max_height"])
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        tokens = _layout_tokens()
        avatar_px = tokens["component"]["avatar"]
        _, btn_h = DESIGN["action_button"]
        btn_min_w = tokens["component"]["button_min_w"]
        icon_px = tokens["space"]["lg"]
        edge = tokens["edge"]["safe"]

        grid = QGridLayout(self)
        grid.setSpacing(tokens["space"]["sm"])
        grid.setContentsMargins(edge, edge, edge, edge)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

        # ===== (0,0) КАРТИНКА: аватар =====
        pic_box = QVBoxLayout()
        pic_box.setSpacing(2)
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(avatar_px, avatar_px)
        self.avatar_label.setScaledContents(True)
        pic_box.addWidget(self.avatar_label)
        pic_box.addStretch(1)
        grid.addLayout(pic_box, 0, 0)

        # ===== (0,1) ПРОФИЛЬ: ник + статус =====
        prof_box = QVBoxLayout()
        prof_box.setSpacing(1)

        # Никнейм (кликабельный, перенос по словам и по буквам)
        self.nickname_label = QLabel(self._wrap_text(tr("nickname_default")))
        self.nickname_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.nickname_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        self.nickname_label.setFont(font)
        self.nickname_label.mousePressEvent = self._on_nickname_clicked
        prof_box.addWidget(self.nickname_label)

        # Статус строка
        self.status_label = QLabel(
            f'<span style="color:#9e9e9e;font-size:13px;">●</span> '
            f'<span style="color:#9e9e9e;">{tr("status_unknown")}</span>'
        )
        self.status_label.setWordWrap(True)
        prof_box.addWidget(self.status_label)

        # "Играет в" (скрыт по умолчанию)
        self.playing_label = QLabel("")
        self.playing_label.setWordWrap(True)
        self.playing_label.setVisible(False)
        prof_box.addWidget(self.playing_label)
        prof_box.addStretch(1)
        grid.addLayout(prof_box, 0, 1)

        # ===== (1,0) ПОСЧИТАТЬ: кнопка + прогресс =====
        calc_box = QVBoxLayout()
        calc_box.setSpacing(tokens["space"]["sm"])

        self.calc_btn = QPushButton(tr("calc_btn_short"))
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setFont(QFont("Segoe UI Emoji", 11))
        self.calc_btn.setIcon(get_section_icon("timer", self.theme))
        self.calc_btn.setIconSize(QSize(icon_px, icon_px))
        self.calc_btn.setFixedHeight(btn_h)
        self.calc_btn.setMinimumWidth(btn_min_w)
        self.calc_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.calc_btn.setEnabled(False)
        calc_box.addWidget(self.calc_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumWidth(btn_min_w)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setFixedHeight(tokens["space"]["lg"])
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setVisible(False)
        calc_box.addWidget(self.progress_bar)
        calc_box.addStretch(1)
        grid.addLayout(calc_box, 1, 0)

        # ===== (1,1) ОБЩЕЕ ВРЕМЯ =====
        total_box = QVBoxLayout()
        total_box.setSpacing(1)

        self.total_time_label = QLabel("")
        self.total_time_label.setWordWrap(True)
        font_time = QFont()
        font_time.setPointSize(11)
        self.total_time_label.setFont(font_time)
        total_box.addWidget(self.total_time_label)
        total_box.addStretch(1)
        grid.addLayout(total_box, 1, 1)

        # Сетевой менеджер для аватара создаём лениво: QNetworkAccessManager
        # тянет Qt5Network + bearer-стек ОС (~15 DLL). Нужен только тогда,
        # когда профиль проверен и грузится аватар.
        self._nam = None

        self.apply_theme(self.theme)

    @staticmethod
    def _wrap_text(text: str) -> str:
        """Невидимые точки разрыва: перенос по словам, при нужде — по буквам."""
        return chr(8203).join(text)  # U+200B zero-width space

    def _on_nickname_clicked(self, event):
        if not self.steam_url:
            return
        self._show_profile_dialog()

    def _show_profile_dialog(self):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(tr("dlg_profile_title"))
        dialog.setMinimumSize(360, 180)
        dialog.setMaximumSize(480, 220)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        icon = QLabel("👤")
        icon.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(32)
        icon.setFont(font)
        layout.addWidget(icon)

        msg = QLabel(tr("dlg_profile_text").format(self.nickname_label.text()))
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        no_btn = QPushButton(tr("dlg_cancel"))
        no_btn.setMinimumHeight(36)
        no_btn.setMinimumWidth(100)
        no_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(no_btn)

        yes_btn = QPushButton(tr("dlg_profile_go"))
        yes_btn.setMinimumHeight(36)
        yes_btn.setMinimumWidth(100)
        yes_btn.setDefault(True)
        yes_btn.clicked.connect(lambda: (
            QDesktopServices.openUrl(QUrl(self.steam_url)), dialog.accept()
        ))
        btn_layout.addWidget(yes_btn)

        layout.addLayout(btn_layout)

        is_dark = self.theme == "dark"
        bg = "#2a2a2a" if is_dark else "#ffffff"
        text = "#f0f0f0" if is_dark else "#333333"
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
            }}
            QLabel {{
                color: {text};
            }}
            QPushButton {{
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: #0055aa;
            }}
            QPushButton#secondary {{
                background-color: #6c757d;
            }}
            QPushButton#secondary:hover {{
                background-color: #5a6268;
            }}
        """)
        no_btn.setObjectName("secondary")
        dialog.exec_()

    def set_nickname(self, nickname: str, steam_url: str = ""):
        self.nickname_label.setText(self._wrap_text(nickname))
        self.steam_url = steam_url

    def _nam_ensure(self) -> QNetworkAccessManager:
        """Создаёт QNetworkAccessManager при первом обращении."""
        if self._nam is None:
            self._nam = QNetworkAccessManager(self)
            self._nam.finished.connect(self._on_avatar_loaded)
        return self._nam

    def set_avatar(self, url: str):
        self._avatar_url = url
        if url:
            request = QNetworkRequest(QUrl(url))
            self._nam_ensure().get(request)
        else:
            self.avatar_label.clear()

    def _on_avatar_loaded(self, reply):
        if reply.error() == reply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                avatar_px = _layout_tokens()["component"]["avatar"]
                scaled = pixmap.scaled(
                    avatar_px, avatar_px,
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                self.avatar_label.setPixmap(scaled)
        reply.deleteLater()

    def set_status(self, status_text: str, color: str = "#9e9e9e", game_name: str = ""):
        # Запоминаем данные — refresh_type_scale перерисует их под шрифт
        self._status_text = status_text
        self._status_color = color
        self._game_name = game_name
        self._render_status()

    def _render_status(self):
        """Рисует статус rich-текстом в масштабе шрифта приложения."""
        from PyQt5.QtWidgets import QApplication
        base = QApplication.instance().font().pointSize() or 10
        dot = max(11, round(base * 1.25))
        small = max(10, round(base * 1.1))
        color = getattr(self, "_status_color", "#9e9e9e")
        status_text = getattr(self, "_status_text", tr("status_unknown"))
        game_name = getattr(self, "_game_name", "")
        self.status_label.setText(
            f'<span style="color:{color};font-size:{dot}px;">●</span> '
            f'<span style="color:{color};">{status_text}</span>'
        )
        if game_name:
            self.playing_label.setText(
                f'<span style="font-size:{small}px;font-style:italic;">'
                f'🎮 {tr("status_playing_in")}: {game_name}</span>'
            )
            self.playing_label.setVisible(True)
        else:
            self.playing_label.setVisible(False)

    def refresh_type_scale(self):
        """Переприменяет семейство и масштаб шрифта (после смены в настройках)."""
        from PyQt5.QtWidgets import QApplication
        base = QApplication.instance().font()
        fam = base.family()
        sz = base.pointSize() or 10
        nick = QFont(fam, max(8, sz + 2))
        nick.setBold(True)
        self.nickname_label.setFont(nick)
        self.total_time_label.setFont(QFont(fam, max(8, sz - 1)))
        self._render_status()

    def set_total_time(self, hours: str, minutes: str):
        self.total_time_label.setText(tr("total_time").format(hours, minutes))

    def set_progress(self, value: int):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)

    def apply_theme(self, theme: str):
        self.theme = theme
        is_dark = theme == "dark"
        self.calc_btn.setIcon(get_section_icon("timer", theme))

        text_main = "#f0f0f0" if is_dark else "#333333"
        text_secondary = "#aaaaaa" if is_dark else "#666666"
        avatar_bg = "#444444" if is_dark else "#f0f0f0"
        avatar_border = "#666666" if is_dark else "#cccccc"

        self.nickname_label.setStyleSheet(f"color: {text_main};")
        self.status_label.setStyleSheet(f"color: {text_secondary}; font-size: 13px;")
        self.playing_label.setStyleSheet(
            f"color: {text_secondary}; font-size: 12px; font-style: italic;"
        )
        self.total_time_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")

        self.avatar_label.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {avatar_border};
                border-radius: 8px;
                background-color: {avatar_bg};
            }}
        """)

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {'#444444' if is_dark else '#e8e8e8'};
                border: none;
                border-radius: 6px;
                text-align: center;
                font-size: 11px;
                color: {text_main};
            }}
            QProgressBar::chunk {{
                background-color: {'#4da6ff' if is_dark else '#0066cc'};
                border-radius: 6px;
            }}
        """)

        self.setStyleSheet(f"""
            QGroupBox {{
                color: {text_secondary};
                font-weight: bold;
                border: 1px solid {'#444444' if is_dark else '#e0e0e0'};
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """)