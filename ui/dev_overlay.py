# ui/dev_overlay.py
"""Dev-overlay направляющих сетки (ШАГ 6 спеки).

Включается только переменной окружения SPV_GUIDES=1, по умолчанию
на UI не влияет никак. Рисует рамку edge.safe и красным подсвечивает
виджеты, чьи margins/spacing вне шкалы tokens/layout.json.
"""

from PyQt5.QtCore import QObject, QEvent, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from app.layout_tokens import tokens as _layout_tokens


def load_tokens():
    return _layout_tokens()


class GuidesOverlay(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self._tokens = load_tokens()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.resize(window.size())

    def _bad_widgets(self):
        scale = set(self._tokens["space"].values())
        bad = []

        def vals(layout):
            m = layout.contentsMargins()
            return [m.left(), m.top(), m.right(), m.bottom(), layout.spacing()]

        for w in self._window.findChildren(QWidget):
            lay = w.layout()
            if lay is None:
                continue
            if any(v not in scale for v in vals(lay)):
                bad.append(w)
        return bad

    def paintEvent(self, event):
        t = self._tokens
        edge = t["edge"]["safe"]
        p = QPainter(self)
        p.setPen(QPen(QColor(t["overlay"]["guide_color"]), 1, Qt.DashLine))
        p.drawRect(edge, edge, self.width() - 2 * edge, self.height() - 2 * edge)
        p.setPen(QPen(QColor(t["overlay"]["error_color"]), 2))
        for w in self._bad_widgets():
            g = w.geometry()
            p.drawRect(g.adjusted(0, 0, -1, -1))
        p.end()


class _ResizeFilter(QObject):
    def __init__(self, window, overlay):
        super().__init__(window)
        self._overlay = overlay

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self._overlay.resize(obj.size())
            self._overlay.update()
        return False


def install_guides(window):
    """Вешает overlay на окно. Вызывать только под SPV_GUIDES=1."""
    overlay = GuidesOverlay(window)
    window.installEventFilter(_ResizeFilter(window, overlay))
    overlay.show()
    overlay.raise_()
    return overlay
