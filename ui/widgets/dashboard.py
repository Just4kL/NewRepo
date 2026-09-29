# ui/widgets/dashboard.py
"""Динамическая сетка главного окна.

Карточки (аутентификация / профиль / таблица) живут в сетке QGridLayout
и могут свободно перемещаться пользователем:

- режим сетки включается кнопкой-замком в нижней панели;
- в режиме сетки у каждой карточки видна ручка «⠿» — перетаскивание
  за неё меняет порядок карточек (drag-and-drop);
- кнопка «–» сворачивает карточку до заголовка;
- порядок, свёрнутость и режим запоминаются через QSettings;
- при растягивании окна за угол растёт только строка с таблицей —
  остальные карточки зафиксированы по высоте (SizePolicy Maximum);
- уже `narrow_breakpoint` сетка складывается в одну колонку.

Современный стандарт: контент тянется, chrome — нет.
"""

from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QToolButton, QGroupBox, QApplication,
)
from PyQt5.QtCore import Qt, QMimeData, QSettings
from PyQt5.QtGui import QDrag

from app.i18n import tr
from ui.gui import DESIGN, SETTINGS_APP, SETTINGS_ORG

CARD_MIME = "application/x-spv-card-id"


class GripHandle(QLabel):
    """Ручка для перетаскивания карточки. Видна только в режиме сетки."""

    def __init__(self, card_id: str, parent=None):
        super().__init__("⠿", parent)
        self.card_id = card_id
        self.setObjectName("GripHandle")
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip(tr("card_drag_tooltip"))
        self._drag_start = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            dist = (event.pos() - self._drag_start).manhattanLength()
            if dist >= QApplication.startDragDistance():
                drag = self._build_drag()
                drag.exec_(Qt.MoveAction)
                self._drag_start = None
        super().mouseMoveEvent(event)

    def _build_drag(self):
        """QDrag с живым скриншотом карточки (без exec — для тестов)."""
        from PyQt5.QtCore import QPoint
        card = self.parentWidget()
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(CARD_MIME, self.card_id.encode("utf-8"))
        drag.setMimeData(mime)
        try:
            pix = card.grab()
            if not pix.isNull():
                drag.setPixmap(pix)
                drag.setHotSpot(QPoint(self.x() + self._drag_start.x(),
                                       self.y() + self._drag_start.y()))
        except Exception:
            pass
        return drag

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)


class MovableCard(QWidget):
    """Прозрачная обёртка над QGroupBox: ручка + сворачивание.

    Сама карточка (рамка, заголовок, фон) рисуется исходным QGroupBox —
    общий стиль не меняется. Обёртка добавляет только тонкую служебную
    строку сверху и управляет политикой роста.
    """

    def __init__(self, card_id: str, content: QGroupBox, grow: bool = False,
                 parent=None, on_state_changed=None):
        super().__init__(parent)
        self.card_id = card_id
        self.content = content
        self._on_state_changed = on_state_changed

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)
        header.setSpacing(4)

        self.grip = GripHandle(card_id, self)
        header.addWidget(self.grip)
        header.addStretch(1)

        self.collapse_btn = QToolButton(self)
        self.collapse_btn.setObjectName("CollapseButton")
        self.collapse_btn.setText("–")
        self.collapse_btn.setAutoRaise(True)
        self.collapse_btn.setMinimumSize(16, 16)
        self.collapse_btn.clicked.connect(self.toggle_collapsed)
        header.addWidget(self.collapse_btn)
        outer.addLayout(header)

        # reparent: карточка переезжает внутрь обёртки, ссылка у окна жива
        outer.addWidget(content)

        from PyQt5.QtWidgets import QSizePolicy
        if grow:
            # Растёт только контентная карточка (таблица)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            # Chrome-карточки: по контенту, лишний рост окна им не достаётся
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self._collapsed = False
        self.retranslate()

    # ==================== API ====================

    def set_edit_mode(self, on: bool):
        self.grip.setVisible(on)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, on: bool):
        self._collapsed = on
        self.content.setVisible(not on)
        self.retranslate()

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)
        if self._on_state_changed is not None:
            self._on_state_changed()

    def set_highlight(self, on: bool):
        self.setProperty("dropTarget", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def retranslate(self):
        self.grip.setToolTip(tr("card_drag_tooltip"))
        self.collapse_btn.setToolTip(
            tr("card_expand_tooltip") if self._collapsed
            else tr("card_collapse_tooltip")
        )
        self.collapse_btn.setText("+" if self._collapsed else "–")


class DashboardGrid(QWidget):
    """Контейнер сетки с drag-and-drop переупорядочиванием карточек."""

    def __init__(self, parent=None, table_card: str = "table",
                 settings: Optional[QSettings] = None):
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setSpacing(DESIGN["spacing"])
        self._grid.setContentsMargins(0, 0, 0, 0)

        self._cards: Dict[str, MovableCard] = {}
        self._order: List[str] = []
        self._table_card = table_card
        self._edit_mode = False
        self._highlighted: Optional[MovableCard] = None

        self._settings = settings or QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._saved_order = self._settings.value("dashboard/order", [], type=list)
        self._saved_collapsed = self._settings.value(
            "dashboard/collapsed", {}, type=dict)
        self._edit_mode = self._settings.value(
            "dashboard/edit_mode", False, type=bool)

        self.setAcceptDrops(True)

    # ==================== ПУБЛИЧНОЕ API ====================

    def add_card(self, card_id: str, widget: QGroupBox, grow: bool = False):
        """Оборачивает секцию и ставит в сетку."""
        card = MovableCard(card_id, widget, grow=grow, parent=self,
                           on_state_changed=self._save_state)
        card.set_edit_mode(self._edit_mode)
        if str(self._saved_collapsed.get(card_id, "0")) == "1":
            card.set_collapsed(True)
        self._cards[card_id] = card
        if card_id in self._saved_order and card_id not in self._order:
            # вставляем по сохранённой позиции
            pos = self._saved_order.index(card_id)
            self._order.insert(min(pos, len(self._order)), card_id)
        elif card_id not in self._order:
            self._order.append(card_id)
        self.relayout()

    def order(self) -> List[str]:
        return list(self._order)

    def card(self, card_id: str) -> Optional[MovableCard]:
        return self._cards.get(card_id)

    def move_card(self, card_id: str, to_index: int):
        """Программное перемещение (и то же вызывается при drop)."""
        if card_id not in self._order:
            return
        to_index = max(0, min(to_index, len(self._order) - 1))
        self._order.remove(card_id)
        self._order.insert(to_index, card_id)
        self.relayout()
        self._save_state()

    def is_edit_mode(self) -> bool:
        return self._edit_mode

    def set_edit_mode(self, on: bool):
        self._edit_mode = on
        for card in self._cards.values():
            card.set_edit_mode(on)
        self._save_state()

    def retranslate(self):
        for card in self._cards.values():
            card.retranslate()

    # ==================== РАСКЛАДКА ====================

    def relayout(self):
        """Расставляет карточки: широко — 2 колонки, узко — 1."""
        while self._grid.count():
            self._grid.takeAt(0)

        cards = [self._cards[cid] for cid in self._order if cid in self._cards]
        if not cards:
            return

        # сбрасываем стретчи в пределах используемой области: иначе пустые
        # строки/колонки от прошлой раскладки крадут место у таблицы
        for r in range(len(cards) + 1):
            self._grid.setRowStretch(r, 0)
        for c in range(3):
            self._grid.setColumnStretch(c, 0)

        narrow = self.width() < DESIGN["narrow_breakpoint"]

        def row_for(card) -> int:
            return 1 if card.card_id == self._table_card else 0

        if narrow or len(cards) <= 2:
            for r, card in enumerate(cards):
                self._grid.addWidget(card, r, 0, 1, 2)
                self._grid.setRowStretch(r, row_for(card))
        else:
            self._grid.addWidget(cards[0], 0, 0)
            self._grid.addWidget(cards[1], 0, 1)
            self._grid.setRowStretch(
                0, 1 if self._table_card in (cards[0].card_id, cards[1].card_id) else 0)
            for r, card in enumerate(cards[2:], start=1):
                self._grid.addWidget(card, r, 0, 1, 2)
                self._grid.setRowStretch(r, row_for(card))

        s0, s1 = DESIGN["wide_stretches"]
        self._grid.setColumnStretch(0, s0)
        self._grid.setColumnStretch(1, s1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # пересчитываем колонки только при пересечении брейкпоинта
        was_narrow = getattr(self, "_was_narrow", None)
        is_narrow = self.width() < DESIGN["narrow_breakpoint"]
        if was_narrow is None or was_narrow != is_narrow:
            self._was_narrow = is_narrow
            self.relayout()

    # ==================== DRAG-AND-DROP ====================

    def _card_at(self, pos) -> Optional[MovableCard]:
        child = self.childAt(pos)
        while child is not None and child is not self:
            if isinstance(child, MovableCard):
                return child
            child = child.parentWidget()
        return None

    def _set_highlight(self, card: Optional[MovableCard]):
        if self._highlighted is not None and self._highlighted is not card:
            self._highlighted.set_highlight(False)
        self._highlighted = card
        if card is not None:
            card.set_highlight(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME) and self._edit_mode:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(CARD_MIME) or not self._edit_mode:
            event.ignore()
            return
        self._set_highlight(self._card_at(event.pos()))
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_highlight(None)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._set_highlight(None)
        if not event.mimeData().hasFormat(CARD_MIME) or not self._edit_mode:
            event.ignore()
            return
        moving = bytes(event.mimeData().data(CARD_MIME)).decode("utf-8")
        target = self._card_at(event.pos())
        if moving in self._order and target is not None and target.card_id != moving:
            self.move_card(moving, self._order.index(target.card_id))
        event.acceptProposedAction()

    # ==================== СОСТОЯНИЕ ====================

    def _save_state(self):
        self._settings.setValue("dashboard/order", self._order)
        collapsed = {cid: ("1" if c.is_collapsed() else "0")
                     for cid, c in self._cards.items()}
        self._settings.setValue("dashboard/collapsed", collapsed)
        self._settings.setValue("dashboard/edit_mode", self._edit_mode)
