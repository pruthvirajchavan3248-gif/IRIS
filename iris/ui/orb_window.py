"""
IRIS Holographic Floating AI Orb Widget
A sleek, futuristic, frameless desktop orb with custom particle glow, state-reactive animations,
and draggable Windows positioning.
"""

import sys
import math
from typing import Optional, Callable
from PySide6.QtCore import Qt, QPoint, QTimer, QRectF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QRadialGradient,
    QLinearGradient,
    QPen,
    QBrush,
    QPainterPath,
    QCursor,
    QFont,
    QAction,
)
from PySide6.QtWidgets import QWidget, QMenu, QApplication

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.state import AssistantState, StateManager
from ..core.events import EventBus, EventType, Event
from ..database.db import get_db

logger = get_logger("orb_window")


class FloatingOrbWindow(QWidget):
    """Futuristic Floating Holographic AI Orb for IRIS."""

    def __init__(self, on_orb_clicked: Optional[Callable[[], None]] = None):
        super().__init__()
        self.config = get_config()
        self.db = get_db()
        self.state_manager = StateManager()
        self.event_bus = EventBus()
        self.on_orb_clicked = on_orb_clicked

        # Window attributes: Frameless, Always on Top, Translucent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.orb_size = self.config.orb_size
        self.resize(self.orb_size, self.orb_size)

        # Restore saved position from DB or place near bottom-right screen corner
        self._init_position()

        # Dragging support
        self._drag_active = False
        self._drag_position = QPoint()

        # Animation state variables
        self._pulse_phase = 0.0
        self._rotation_angle = 0.0
        self._wave_phase = 0.0

        # Animation timer (60 FPS refresh rate)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(16)  # ~60 FPS

        self._subscribe_events()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _init_position(self) -> None:
        """Positions the orb at user saved position or bottom right of primary screen."""
        screen = QApplication.primaryScreen().geometry()
        saved_x = self.db.get_preference("orb_x")
        saved_y = self.db.get_preference("orb_y")

        if saved_x and saved_y and saved_x.isdigit() and saved_y.isdigit():
            x = int(saved_x)
            y = int(saved_y)
        else:
            x = screen.width() - self.orb_size - 40
            y = screen.height() - self.orb_size - 80

        self.move(x, y)

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(EventType.STATE_CHANGED, self._on_state_changed)
        self.event_bus.subscribe(EventType.ORB_VISIBILITY_TOGGLED, self._on_visibility_toggled)

    def _on_state_changed(self, event: Event) -> None:
        self.update()

    def _on_visibility_toggled(self, event: Event) -> None:
        visible = event.data.get("visible", True)
        if visible:
            self.show()
        else:
            self.hide()

    def _update_animation(self) -> None:
        """Updates phase angles for orbital rings and pulsing glow."""
        state = self.state_manager.current_state

        if state == AssistantState.THINKING:
            self._rotation_angle = (self._rotation_angle + 6.0) % 360
            self._pulse_phase += 0.12
        elif state == AssistantState.SPEAKING:
            self._rotation_angle = (self._rotation_angle + 3.0) % 360
            self._wave_phase += 0.15
            self._pulse_phase += 0.08
        elif state == AssistantState.LISTENING:
            self._pulse_phase += 0.15
            self._rotation_angle = (self._rotation_angle + 2.0) % 360
        else:  # IDLE or MUTED
            self._pulse_phase += 0.03
            self._rotation_angle = (self._rotation_angle + 0.8) % 360

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._was_dragged = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._drag_active and (event.buttons() & Qt.MouseButton.LeftButton):
            current_pos = event.globalPosition().toPoint()
            # Check if user has moved more than 5 pixels (real drag vs accidental movement)
            delta = current_pos - self._drag_start_pos
            if abs(delta.x()) > 5 or abs(delta.y()) > 5:
                self._was_dragged = True
            self.move(current_pos - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            # Save new position to database
            pos = self.pos()
            self.db.set_preference("orb_x", str(pos.x()))
            self.db.set_preference("orb_y", str(pos.y()))
            
            # Only trigger orb tap if user did NOT drag (tap = click without moving)
            if not self._was_dragged and self.on_orb_clicked:
                self.on_orb_clicked()
            event.accept()

    def _show_context_menu(self, global_pos: QPoint) -> None:
        """Displays right click context menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #38bdf8;
            }
        """)

        # Mute/Unmute
        is_muted = self.state_manager.is_muted
        mute_action = QAction("Unmute Microphone" if is_muted else "Mute Microphone", self)
        mute_action.triggered.connect(self.state_manager.toggle_mute)
        menu.addAction(mute_action)

        # Settings & Database Viewer
        settings_action = QAction("Memory & Settings Viewer", self)
        settings_action.triggered.connect(lambda: self.event_bus.emit(EventType.SETTINGS_REQUESTED))
        menu.addAction(settings_action)

        # Hide Orb
        hide_action = QAction("Hide Orb (Background Mode)", self)
        hide_action.triggered.connect(lambda: self.state_manager.set_orb_visible(False))
        menu.addAction(hide_action)

        menu.addSeparator()

        # Exit
        exit_action = QAction("Exit IRIS", self)
        exit_action.triggered.connect(lambda: self.event_bus.emit(EventType.SYSTEM_SHUTDOWN))
        menu.addAction(exit_action)

        menu.exec(global_pos)

    def paintEvent(self, event):
        """Custom painter creating futuristic glowing holographic rings and central orb."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width / 2.0
        center_y = height / 2.0
        radius = min(width, height) / 2.0 - 12.0

        state = self.state_manager.current_state

        # Color schemes mapped to state
        if state == AssistantState.IDLE:
            core_c1 = QColor(0, 240, 255, 230)      # Cyan
            core_c2 = QColor(0, 100, 255, 180)      # Electric Blue
            glow_col = QColor(0, 220, 255, 80)
            ring_col = QColor(0, 240, 255, 160)
        elif state == AssistantState.LISTENING:
            core_c1 = QColor(217, 70, 239, 240)    # Neon Magenta
            core_c2 = QColor(139, 92, 246, 200)    # Violet
            glow_col = QColor(217, 70, 239, 120)
            ring_col = QColor(244, 114, 182, 220)
        elif state == AssistantState.THINKING:
            core_c1 = QColor(245, 158, 11, 240)    # Amber
            core_c2 = QColor(251, 191, 36, 200)    # Gold
            glow_col = QColor(245, 158, 11, 110)
            ring_col = QColor(252, 211, 77, 230)
        elif state == AssistantState.SPEAKING:
            core_c1 = QColor(16, 185, 129, 240)    # Emerald
            core_c2 = QColor(6, 182, 212, 200)     # Aquamarine
            glow_col = QColor(16, 185, 129, 120)
            ring_col = QColor(52, 211, 153, 230)
        elif state == AssistantState.MUTED:
            core_c1 = QColor(100, 116, 139, 200)   # Slate Grey
            core_c2 = QColor(71, 85, 105, 160)
            glow_col = QColor(100, 116, 139, 40)
            ring_col = QColor(148, 163, 184, 120)
        else:  # ERROR
            core_c1 = QColor(239, 68, 68, 240)     # Crimson
            core_c2 = QColor(185, 28, 28, 200)
            glow_col = QColor(239, 68, 68, 120)
            ring_col = QColor(248, 113, 113, 220)

        # 1. Outer Diffuse Glow
        pulse_scale = 1.0 + 0.08 * math.sin(self._pulse_phase)
        glow_radius = radius * 1.35 * pulse_scale
        glow_grad = QRadialGradient(center_x, center_y, glow_radius)
        glow_grad.setColorAt(0.0, glow_col)
        glow_grad.setColorAt(0.6, QColor(glow_col.red(), glow_col.green(), glow_col.blue(), int(glow_col.alpha() * 0.3)))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(center_x - glow_radius, center_y - glow_radius, glow_radius * 2, glow_radius * 2))

        # 2. Holographic Rotating Segmented Tech Ring
        ring_radius = radius * 1.05
        ring_rect = QRectF(center_x - ring_radius, center_y - ring_radius, ring_radius * 2, ring_radius * 2)
        pen = QPen(ring_col, 2.2, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw 3 holographic orbiting arcs
        arc_count = 3
        arc_span = 70 * 16  # 70 degrees
        gap_span = (360 / arc_count) * 16
        for i in range(arc_count):
            start_angle = int((self._rotation_angle * 16) + (i * gap_span))
            painter.drawArc(ring_rect, start_angle, arc_span)

        # 3. Inner Counter-Rotating Ring (Smaller dots / subtle ring)
        inner_ring_radius = radius * 0.88
        inner_rect = QRectF(center_x - inner_ring_radius, center_y - inner_ring_radius, inner_ring_radius * 2, inner_ring_radius * 2)
        inner_pen = QPen(QColor(ring_col.red(), ring_col.green(), ring_col.blue(), 100), 1.2, Qt.PenStyle.DashLine)
        painter.setPen(inner_pen)
        painter.drawArc(inner_rect, int(-self._rotation_angle * 16 * 1.5), 360 * 16)

        # 4. Central Holographic Core Sphere
        core_radius = radius * 0.68 * (1.0 + 0.04 * math.sin(self._pulse_phase * 1.5))
        core_grad = QRadialGradient(center_x - core_radius * 0.3, center_y - core_radius * 0.3, core_radius * 1.2)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 240))  # Specular bright center
        core_grad.setColorAt(0.2, core_c1)
        core_grad.setColorAt(0.8, core_c2)
        core_grad.setColorAt(1.0, QColor(core_c2.red(), core_c2.green(), core_c2.blue(), 120))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QRectF(center_x - core_radius, center_y - core_radius, core_radius * 2, core_radius * 2))

        # 5. Core Branding / State Glyph
        painter.setPen(QPen(QColor(255, 255, 255, 220)))
        font = QFont("Segoe UI", int(self.orb_size * 0.12), QFont.Weight.Bold)
        painter.setFont(font)
        
        if state == AssistantState.MUTED:
            # Draw Muted cross or "OFF"
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, "MUTED")
        elif state == AssistantState.THINKING:
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, "...")
        else:
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, "IRIS")
