"""
Painted components. Everything is QPainter — no images, no blur effects
(a blur forces a full repaint of the widget tree on every frame).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .theme import ACCENT, BAD, DIM, FAINT, GHOST, LINE, LINE_HI, PANEL_HI, TEXT


def _font(size, weight=QFont.Normal, spacing=0.0, family="Rajdhani"):
    f = QFont(family, size)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


# ===========================================================================
class DotField(QWidget):
    """Static dot grid + vignette. Gives the dark field some depth."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        c = QColor(255, 255, 255, 9)
        step = 26
        for y in range(step, h, step):
            for x in range(step, w, step):
                p.fillRect(QRectF(x, y, 1, 1), c)
        p.end()


# ===========================================================================
class StatCell(QWidget):
    """One label-over-value readout in the header strip."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.label = label
        self.value = "—"
        self.sub = ""
        self.flagged = False
        self.setMinimumWidth(118)
        self.setFixedHeight(46)

    def set(self, value: str, sub: str = "", flagged: bool = False):
        self.value, self.sub, self.flagged = value or "—", sub, flagged
        self.setToolTip(f"{value} {sub}".strip())
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()

        p.setFont(_font(7, QFont.DemiBold, 2.4))
        p.setPen(QColor(FAINT))
        p.drawText(QPointF(0, 11), self.label)

        p.setFont(_font(11, QFont.DemiBold, 0.2))
        p.setPen(QColor(BAD if self.flagged else TEXT))
        fm = p.fontMetrics()
        p.drawText(QPointF(0, 29), fm.elidedText(self.value, Qt.ElideRight, w - 6))

        if self.sub:
            p.setFont(_font(8, QFont.Normal, 1.4))
            p.setPen(QColor(FAINT))
            p.drawText(QPointF(0, 42), self.sub)
        p.end()


# ===========================================================================
class StepBar(QWidget):
    """Segmented meter: how many steps this profile runs, out of the max."""

    def __init__(self, count: int, total: int, parent=None):
        super().__init__(parent)
        self.count, self.total = count, total
        self.active = False
        self.setFixedHeight(6)

    def set_active(self, on: bool):
        self.active = on
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        gap = 3.0
        seg = (w - gap * (self.total - 1)) / self.total
        for i in range(self.total):
            x = i * (seg + gap)
            lit = i < self.count
            if lit:
                col = QColor(ACCENT) if self.active else QColor(FAINT)
            else:
                col = QColor(GHOST)
            p.fillRect(QRectF(x, 0, seg, h), col)
        p.end()


# ===========================================================================
class ProfileTile(QWidget):
    """A whole profile as one selectable card."""

    clicked = Signal(str)

    def __init__(self, key: str, data: dict, max_steps: int, parent=None):
        super().__init__(parent)
        self.key = key
        self.data = data
        self.selected = False
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(316)

        self.meter = StepBar(len(data["steps"]), max_steps, self)

    def resizeEvent(self, _e):
        self.meter.setGeometry(28, self.height() - 40, self.width() - 56, 6)

    def set_selected(self, on: bool):
        self.selected = on
        self.meter.set_active(on)
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, _e):
        self.clicked.emit(self.key)

    # ------------------------------------------------------------------
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        body = QRectF(0.5, 0.5, w - 1, h - 1)

        if self.selected:
            p.fillRect(body, QColor(255, 255, 255, 13))
            border, ink, sub_ink = QColor(255, 255, 255, 205), QColor(TEXT), QColor(DIM)
        else:
            p.fillRect(body, QColor(PANEL_HI))
            a = 110 if self._hover else 52
            border = QColor(255, 255, 255, a)
            ink = QColor(DIM if self._hover else "#7E8087")
            sub_ink = QColor(FAINT)

        pen = QPen(border)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(body)

        if self.selected:
            p.fillRect(QRectF(0, 0, 3, h), QColor(ACCENT))

        # ---- index, drawn as a large outline numeral ----
        p.setFont(_font(44, QFont.Bold, 1.0))
        p.setPen(QColor(255, 255, 255, 30 if not self.selected else 52))
        p.drawText(QPointF(26, 68), self.data["index"])

        # ---- impact chip ----
        chip_w = 104
        chip = QRectF(w - chip_w - 24, 28, chip_w, 20)
        cpen = QPen(QColor(255, 255, 255, 150 if self.selected else 60))
        cpen.setWidthF(1.0)
        p.setPen(cpen)
        p.drawRect(chip)
        p.setFont(_font(7, QFont.DemiBold, 2.0))
        p.setPen(QColor(TEXT if self.selected else FAINT))
        p.drawText(chip, Qt.AlignCenter, self.data["impact"])

        # ---- name / sub ----
        p.setFont(_font(25, QFont.Bold, 2.0))
        p.setPen(ink)
        p.drawText(QPointF(26, 112), self.data["name"])

        p.setFont(_font(8, QFont.DemiBold, 3.0))
        p.setPen(sub_ink)
        p.drawText(QPointF(27, 130), self.data["sub"])

        # ---- rule ----
        p.setPen(QPen(QColor(LINE_HI if self.selected else LINE), 1.0))
        p.drawLine(QPointF(26, 148.5), QPointF(w - 24, 148.5))

        # ---- bullets ----
        p.setFont(QFont("Noto Sans Thai", 8))
        y = 170
        for line in self.data["bullets"]:
            p.setPen(QColor(255, 255, 255, 95 if self.selected else 60))
            p.drawText(QPointF(26, y), "—")
            p.setPen(QColor(DIM if self.selected else "#74767D"))
            for seg in _wrap(p, line, w - 76):
                p.drawText(QPointF(44, y), seg)
                y += 16
            y += 6

        # ---- step count, above the meter ----
        p.setFont(_font(7, QFont.DemiBold, 2.2))
        p.setPen(QColor(FAINT))
        p.drawText(QPointF(28, h - 50), f"{len(self.data['steps'])} STEPS")
        p.end()


def _wrap(p, text: str, width: float):
    fm = p.fontMetrics()
    if fm.horizontalAdvance(text) <= width:
        return [text]
    out, cur = [], ""
    for word in text.split(" "):
        probe = f"{cur} {word}".strip()
        if fm.horizontalAdvance(probe) <= width:
            cur = probe
        else:
            if cur:
                out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


# ===========================================================================
class ActionButton(QWidget):
    """Flat bar button. Primary is filled, ghost is outlined."""

    clicked = Signal()

    def __init__(self, title, sub="", primary=True, parent=None):
        super().__init__(parent)
        self.title, self.sub, self.primary = title, sub, primary
        self._hover = False
        self._down = False
        self._enabled = True
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(58 if primary else 50)

    def set_text(self, title=None, sub=None):
        if title is not None:
            self.title = title
        if sub is not None:
            self.sub = sub
        self.update()

    def set_enabled(self, on: bool):
        self._enabled = on
        self.setCursor(Qt.PointingHandCursor if on else Qt.ForbiddenCursor)
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = self._down = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, _e):
        if self._enabled:
            self._down = True
            self.update()

    def mouseReleaseEvent(self, e):
        was = self._down
        self._down = False
        self.update()
        if was and self._enabled and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = QRectF(0.5, 0.5, w - 1, h - 1)

        if not self._enabled:
            p.fillRect(r, QColor(255, 255, 255, 8))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawRect(r)
            ink = QColor(FAINT)
        elif self.primary:
            base = 255 if not self._down else 225
            p.fillRect(r, QColor(base, base, base, 255 if self._hover else 234))
            ink = QColor("#07080A")
        else:
            p.fillRect(r, QColor(255, 255, 255, 16 if self._hover else 6))
            p.setPen(QPen(QColor(255, 255, 255, 120 if self._hover else 55), 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawRect(r)
            ink = QColor(TEXT if self._hover else DIM)

        p.setFont(_font(14 if self.primary else 12, QFont.Bold, 4.0))
        p.setPen(ink)
        baseline = h / 2 + (-2 if self.sub else 5)
        p.drawText(QPointF(26, baseline), self.title)

        if self.sub:
            p.setFont(QFont("Noto Sans Thai", 8))
            p.setPen(QColor("#4C4E55") if self.primary and self._enabled
                     else QColor(FAINT))
            p.drawText(QPointF(27, h / 2 + 15), self.sub)
        p.end()


# ===========================================================================
class ScanBar(QWidget):
    """Progress hairline. Indeterminate sweep until a total arrives."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self.value = 0.0
        self.sweeping = False
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self.value, self.sweeping = 0.0, True
        self._timer.start(28)
        self.update()

    def set_progress(self, i: int, total: int):
        self.sweeping = False
        self.value = 0.0 if total <= 0 else i / total
        self.update()

    def stop(self):
        self._timer.stop()
        self.sweeping = False
        self.update()

    def _tick(self):
        self._t = (self._t + 0.018) % 1.0
        if self.sweeping:
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(255, 255, 255, 16))
        if self.sweeping:
            bw = w * 0.22
            x = (w + bw) * self._t - bw
            p.fillRect(QRectF(x, 0, bw, h), QColor(ACCENT))
        elif self.value > 0:
            p.fillRect(QRectF(0, 0, w * self.value, h), QColor(ACCENT))
        p.end()


# ===========================================================================
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(7, 7)
        self.color = QColor(FAINT)
        self.pulse = False
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def set(self, color: str, pulse: bool = False):
        self.color = QColor(color)
        self.pulse = pulse
        self.update()

    def _tick(self):
        if self.pulse:
            self._t = (self._t + 0.06) % 1.0
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(self.color)
        if self.pulse:
            c.setAlphaF(0.45 + 0.55 * abs(math.sin(self._t * math.pi)))
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawEllipse(0, 0, 7, 7)
        p.end()


# ===========================================================================
class Mark(QWidget):
    """Fallback wordmark glyph when assets/logo.png is missing."""

    def __init__(self, size=34, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        pen = QPen(QColor(TEXT))
        pen.setWidthF(1.6)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(s * 0.30, s * 0.18)
        path.lineTo(s * 0.62, s * 0.18)
        path.lineTo(s * 0.78, s * 0.34)
        path.lineTo(s * 0.46, s * 0.50)
        path.lineTo(s * 0.78, s * 0.66)
        path.lineTo(s * 0.62, s * 0.82)
        path.lineTo(s * 0.30, s * 0.82)
        p.drawPath(path)
        p.drawLine(QPointF(s * 0.08, s * 0.50), QPointF(s * 0.40, s * 0.50))
        p.end()
