# ui/language_popup.py
"""Popup выбора языка: Material-список вверх от глобуса.

Почему не QMenu: обрезанный по высоте QMenu ломает скролл, фокус и
позиционирование. Свой виджет даёт полный контроль:
- ровно 6 видимых строк, остальные — нативным скроллом;
- hover-подсветка и «утопленный» selected-стиль (Material);
- стрелки ↑/↓ двигают выбор, Space/Enter применяют;
- открывается вверх от кнопки, у края экрана — вниз.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent

VISIBLE_ROWS = 6


def popup_geometry(btn_top_left, btn_height: int, popup_w: int, popup_h: int,
                   screen_rect) -> "QPoint":
    """Позиция popup: вверх от кнопки; у верхнего края — вниз; по X — в экран."""
    from PyQt5.QtCore import QPoint
    x = min(btn_top_left.x(), screen_rect.right() - popup_w)
    x = max(x, screen_rect.left())
    y = btn_top_left.y() - popup_h
    if y < screen_rect.top():
        y = btn_top_left.y() + btn_height  # fallback вниз
    return QPoint(x, y)


def _palette(theme: str) -> dict:
    if theme == "dark":
        return {"bg": "#2a2a2a", "border": "#555555", "text": "#f0f0f0",
                "hover": "#3a3a3a", "selected": "#4da6ff",
                "selected_text": "#1a1a1a", "pressed": "#3d96ef"}
    return {"bg": "#ffffff", "border": "#cccccc", "text": "#333333",
            "hover": "#e6f0fa", "selected": "#0066cc",
            "selected_text": "#ffffff", "pressed": "#0055aa"}


class _LangList(QListWidget):
    """Список с активацией по Space (Enter работает нативно)."""

    def __init__(self, on_activate, parent=None):
        super().__init__(parent)
        self._on_activate = on_activate
        self.setMouseTracking(True)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._on_activate()
            event.accept()
            return
        super().keyPressEvent(event)


class LanguagePopup(QWidget):
    """Карточка-список языков (Qt.Popup: сама закрывается по клику мимо)."""

    def __init__(self, languages, current_name: str, theme: str,
                 on_select, parent=None):
        super().__init__(parent,
                         Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setObjectName("LanguagePopup")
        self._on_select = on_select

        pal = _palette(theme)
        self.setStyleSheet(
            "QWidget#LanguagePopup {{"
            " background-color: {bg}; border: 1px solid {border};"
            " border-radius: 10px; }}"
            "QListWidget {{ background: transparent; border: none; outline: none;"
            " color: {text}; font-size: 13px; }}"
            "QListWidget::item {{ padding: 7px 12px; border-radius: 6px; }}"
            "QListWidget::item:hover {{ background-color: {hover}; }}"
            "QListWidget::item:selected {{ background-color: {selected};"
            " color: {selected_text}; font-weight: bold;"
            " border: 1px solid {pressed}; }}"
            "".format(**pal)
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self.list = _LangList(self.choose_current, self)
        current_row = 0
        for i, lang in enumerate(languages):
            item = QListWidgetItem(f"{lang['flag']} {lang['native']}")
            item.setData(Qt.UserRole, lang["name"])
            self.list.addItem(item)
            if lang["name"] == current_name:
                current_row = i
        self.list.setCurrentRow(current_row)
        self.list.scrollToItem(self.list.item(current_row))
        self.list.itemClicked.connect(self._on_item)
        self.list.itemActivated.connect(self._on_item)

        row_h = max(1, self.list.sizeHintForRow(0))
        fw = self.list.frameWidth()
        self.list.setFixedHeight(row_h * VISIBLE_ROWS + fw * 2)
        layout.addWidget(self.list)

    # ==================== API ====================

    def row_height(self) -> int:
        return max(1, self.list.sizeHintForRow(0))

    def choose_current(self):
        """Применить текущий ряд (Space/Enter) и закрыться."""
        item = self.list.currentItem()
        if item is not None:
            self._on_select(item.data(Qt.UserRole))
        self.close()

    def show_above(self, btn, screen_rect):
        """Показать вверх от кнопки; у верхнего края — вниз."""
        list_w = (self.list.sizeHintForColumn(0)
                  + self.list.verticalScrollBar().sizeHint().width() + 16)
        w = max(btn.width(), list_w)
        self.list.setFixedWidth(w)
        self.setFixedWidth(w + 8)
        h = self.list.height() + 8
        self.setFixedHeight(h)
        top = btn.mapToGlobal(btn.rect().topLeft())
        pos = popup_geometry(top, btn.height(), w, h, screen_rect)
        self.move(pos)
        self.show()
        self.list.setFocus()

    # ==================== внутреннее ====================

    def _on_item(self, item):
        self._on_select(item.data(Qt.UserRole))
        self.close()
