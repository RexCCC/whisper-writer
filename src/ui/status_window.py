"""
Aurora status HUD for WhisperWriter.

A lightweight, robust, glowing status overlay that replaces the old stylesheet-
pulsing window (which crashed Qt5Core with 0xc0000409 by re-parsing an hsla()
stylesheet ~66x/second and churning the widget across threads).

Design: a frameless, translucent, click-through glass pill, bottom-center.
  - recording    -> warm coral dot with a breathing glow pulse
  - transcribing  -> cool cyan->indigo rotating "comet" ring (processing)
  - idle/error    -> hidden

Robustness: the widget is created ONCE on the GUI thread and never destroyed.
updateStatus() (a queued slot) only flips a state string + shows/hides; a single
GUI-thread QTimer drives ALL painting. No cross-thread Qt calls, no stylesheet
churn -> no more Qt fast-fail crashes.
"""
import sys
import os
import math

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QRectF
from PyQt5.QtGui import (QColor, QPainter, QPen, QBrush, QFont,
                         QRadialGradient, QConicalGradient, QPainterPath)
from PyQt5.QtWidgets import QApplication, QWidget

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from utils import ConfigManager
except Exception:
    ConfigManager = None

# ---- palette -------------------------------------------------------------
GLASS_BG     = QColor(14, 17, 22, 194)      # deep charcoal, ~0.76 alpha
GLASS_BORDER = QColor(255, 255, 255, 28)
TOP_HILITE   = QColor(255, 255, 255, 40)
TEXT_COLOR   = QColor(236, 239, 245)
CORAL        = QColor(255, 90, 110)          # recording
CORAL_GLOW   = QColor(255, 70, 92)
CYAN         = QColor(77, 208, 225)          # processing (tail)
INDIGO       = QColor(124, 108, 255)         # processing (head)
IDLE_SLATE   = QColor(138, 148, 166)


class StatusWindow(QWidget):
    statusSignal = pyqtSignal(str, bool)
    closeSignal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._mode = 'idle'          # 'idle' | 'recording' | 'processing'
        self._label = ''
        self._phase = 0.0            # breathing pulse (0..2pi)
        self._angle = 0.0            # ring rotation (degrees)

        self.setFixedSize(284, 66)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)   # click-through
        self.setAttribute(Qt.WA_ShowWithoutActivating)       # never steal focus

        self._font = QFont('Segoe UI', 11, QFont.Medium)

        # single GUI-thread animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self.statusSignal.connect(self.updateStatus)

    # ---- animation (GUI thread only) ------------------------------------
    def _tick(self):
        self._phase = (self._phase + 0.14) % (2 * math.pi)
        self._angle = (self._angle + 7.0) % 360.0
        self.update()

    # ---- positioning ----------------------------------------------------
    def show(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 120
        self.move(x, y)
        super().show()
        self.raise_()
        if not self._timer.isActive():
            self._timer.start(33)  # ~30 fps

    def _hide(self):
        self._timer.stop()
        self.hide()

    # ---- painting -------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        pad = 12.0
        rect = QRectF(pad, pad, self.width() - 2 * pad, self.height() - 2 * pad)
        radius = rect.height() / 2.0

        if self._mode == 'recording':
            accent = CORAL
        elif self._mode == 'processing':
            accent = INDIGO
        else:
            accent = IDLE_SLATE

        # outer neon bloom (cheap blur via stacked translucent strokes)
        for i in range(6, 0, -1):
            a = int(9 * (i / 6.0) * (1.0 if self._mode != 'idle' else 0.4))
            p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), a), i * 2.2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(-i, -i, i, i), radius + i, radius + i)

        # glass body
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(GLASS_BG))
        p.drawPath(path)
        # top highlight + hairline border
        p.setPen(QPen(TOP_HILITE, 1.2))
        p.drawLine(int(rect.left() + radius), int(rect.top() + 1),
                   int(rect.right() - radius), int(rect.top() + 1))
        p.setPen(QPen(GLASS_BORDER, 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, radius, radius)

        # indicator
        cx = rect.left() + radius + 6
        cy = rect.center().y()
        if self._mode == 'recording':
            self._paint_recording(p, cx, cy)
        elif self._mode == 'processing':
            self._paint_processing(p, cx, cy)

        # label
        p.setPen(QPen(TEXT_COLOR))
        p.setFont(self._font)
        text_rect = QRectF(cx + 20, rect.top(), rect.right() - (cx + 20) - 8, rect.height())
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._label)
        p.end()

    def _paint_recording(self, p, cx, cy):
        bloom = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(self._phase))
        r = 16.0
        g = QRadialGradient(cx, cy, r)
        g.setColorAt(0.0, QColor(CORAL_GLOW.red(), CORAL_GLOW.green(), CORAL_GLOW.blue(), int(150 * bloom)))
        g.setColorAt(1.0, QColor(CORAL_GLOW.red(), CORAL_GLOW.green(), CORAL_GLOW.blue(), 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        dot = 4.6 + 0.8 * (0.5 + 0.5 * math.sin(self._phase))
        p.setBrush(QBrush(CORAL))
        p.drawEllipse(QRectF(cx - dot, cy - dot, 2 * dot, 2 * dot))

    def _paint_processing(self, p, cx, cy):
        r = 9.5
        ring = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        grad = QConicalGradient(cx, cy, -self._angle)
        grad.setColorAt(0.00, QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 0))
        grad.setColorAt(0.55, QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 150))
        grad.setColorAt(0.92, QColor(INDIGO.red(), INDIGO.green(), INDIGO.blue(), 255))
        grad.setColorAt(1.00, QColor(INDIGO.red(), INDIGO.green(), INDIGO.blue(), 0))
        p.setBrush(Qt.NoBrush)
        p.setOpacity(0.35)                                   # soft under-glow
        p.setPen(QPen(QBrush(grad), 6.0, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(ring, 0, 360 * 16)
        p.setOpacity(1.0)                                    # crisp ring
        p.setPen(QPen(QBrush(grad), 2.6, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(ring, 0, 360 * 16)

    # ---- state (queued slot -> always runs on the GUI thread) -----------
    @pyqtSlot(str, bool)
    def updateStatus(self, status, use_llm=False):
        if status == 'recording':
            if ConfigManager is not None:
                try:
                    continuous = ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous'
                    remote = ConfigManager.get_config_value('model_options', 'use_api')
                    allow = ConfigManager.get_config_value('recording_options', 'allow_continuous_api')
                    if use_llm:
                        remote = remote or (ConfigManager.get_config_value('llm_post_processing', 'api_type') != 'ollama')
                    if continuous and remote and not allow:
                        self.closeSignal.emit()   # safety guard preserved
                        return
                except Exception:
                    pass
            self._mode, self._label = 'recording', 'Listening'
            self.show()
        elif status == 'transcribing':
            self._mode, self._label = 'processing', 'Transcribing'
            self.show()
        elif status == 'processing_llm_cleanup':
            self._mode, self._label = 'processing', 'Cleaning up'
            self.show()
        elif status == 'processing_llm_instruction':
            self._mode, self._label = 'processing', 'Thinking'
            self.show()
        elif status in ('idle', 'error', 'cancel'):
            self._mode = 'idle'
            self._hide()
            self.closeSignal.emit()   # preserves main.py's stop_result_thread flow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = StatusWindow()
    w.statusSignal.emit('recording', False)
    QTimer.singleShot(2500, lambda: w.statusSignal.emit('transcribing', False))
    QTimer.singleShot(6000, lambda: w.statusSignal.emit('idle', False))
    sys.exit(app.exec_())
