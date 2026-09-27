# ui/language_dialog.py
"""Диалог выбора языка с поддержкой неограниченного числа языков"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from app.config import LANGUAGES
from app.i18n import TRANSLATIONS
from app.resources import get_app_pixmap, get_app_icon


class LanguageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_language = "Русский"
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.setWindowTitle("Steam Playtime Viewer — Language Selection")
        self.setModal(True)
        self.setFixedSize(480, 420)

        self.setWindowIcon(get_app_icon())

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 20)

        # ===== ИКОНКА =====
        icon_label = QLabel()
        pixmap = get_app_pixmap(64)
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(icon_label)

        # ===== ЗАГОЛОВОК =====
        title = QLabel("🌍 Выбор языка / Language Selection")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        main_layout.addWidget(title)

        subtitle = QLabel("Выберите язык интерфейса / Choose interface language")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888888;")
        main_layout.addWidget(subtitle)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # ===== СПИСОК ЯЗЫКОВ =====
        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(160)

        for lang in LANGUAGES:
            item = QListWidgetItem(f"{lang['flag']} {lang['native']}")
            item.setData(Qt.UserRole, lang['name'])
            item.setToolTip(lang['description'])
            self.list_widget.addItem(item)

        self.list_widget.setCurrentRow(0)
        self.list_widget.currentRowChanged.connect(self.on_selection_changed)
        main_layout.addWidget(self.list_widget)

        # ===== ОПИСАНИЕ =====
        self.description = QLabel(LANGUAGES[0]['description'])
        self.description.setAlignment(Qt.AlignCenter)
        self.description.setWordWrap(True)
        self.description.setStyleSheet("color: #888888; padding: 4px;")
        main_layout.addWidget(self.description)

        # ===== КНОПКИ =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setFixedSize(120, 40)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_continue = QPushButton("Продолжить →")
        self.btn_continue.setFixedSize(140, 40)
        self.btn_continue.setDefault(True)
        self.btn_continue.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_continue)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self._apply_selected_texts(0)

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 10px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                border-radius: 8px;
                padding: 10px;
                margin: 2px 4px;
                color: #333333;
            }
            QListWidget::item:selected {
                background-color: #0066cc;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #e6f0fa;
            }
            QListWidget::item:selected:hover {
                background-color: #0055aa;
            }
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0055aa;
            }
            QPushButton#cancel {
                background-color: #6c757d;
            }
            QPushButton#cancel:hover {
                background-color: #5a6268;
            }
        """)
        self.btn_cancel.setObjectName("cancel")

    def on_selection_changed(self, index):
        if 0 <= index < len(LANGUAGES):
            lang = LANGUAGES[index]
            self.selected_language = lang['name']
            self.description.setText(lang['description'])
            self._apply_selected_texts(index)

    def _apply_selected_texts(self, index):
        """Кнопки — на выбранном языке (читаем словарь напрямую,
        глобальный язык переключается только после Accept)."""
        code = LANGUAGES[index]["code"]
        texts = TRANSLATIONS.get(code, TRANSLATIONS["ru"])
        self.btn_continue.setText(texts.get("lang_continue", "→"))
        self.btn_cancel.setText(texts.get("lang_cancel", "×"))

    def accept(self):
        current = self.list_widget.currentItem()
        if current:
            self.selected_language = current.data(Qt.UserRole)
        super().accept()