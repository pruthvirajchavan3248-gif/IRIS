"""
IRIS Windows System Tray Integration
Provides persistent system tray presence, quick privacy controls, and desktop notification badges.
"""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.events import EventBus, EventType, Event
from ..core.state import StateManager, AssistantState

logger = get_logger("tray_icon")


class IrisTrayIcon(QSystemTrayIcon):
    """Windows System Tray Icon with quick privacy and assistant controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.event_bus = EventBus()
        self.state_manager = StateManager()

        self._setup_icon()
        self._setup_menu()
        self._subscribe_events()

        self.activated.connect(self._on_tray_activated)
        self.show()

    def _create_tray_pixmap(self, is_muted: bool = False) -> QPixmap:
        """Generates dynamic crisp tray icon with glowing iris ring."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Ring color
        ring_color = QColor(100, 116, 139) if is_muted else QColor(0, 240, 255)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ring_color)
        painter.drawEllipse(2, 2, 28, 28)

        # Core dark center
        painter.setBrush(QColor(15, 23, 42))
        painter.drawEllipse(8, 8, 16, 16)

        # Small central indicator dot
        dot_color = QColor(239, 68, 68) if is_muted else QColor(52, 211, 153)
        painter.setBrush(dot_color)
        painter.drawEllipse(13, 13, 6, 6)

        painter.end()
        return pixmap

    def _setup_icon(self) -> None:
        pixmap = self._create_tray_pixmap(self.state_manager.is_muted)
        self.setIcon(QIcon(pixmap))
        self.setToolTip("IRIS — Windows Virtual AI Assistant")

    def _setup_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
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

        # Title
        title_action = QAction("IRIS Virtual Assistant", self)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        # Toggle Mute
        self.mute_action = QAction("Mute Microphone", self)
        self.mute_action.triggered.connect(self._toggle_mute)
        menu.addAction(self.mute_action)

        # Toggle Orb Visibility
        self.orb_action = QAction("Hide Floating Orb", self)
        self.orb_action.triggered.connect(self._toggle_orb)
        menu.addAction(self.orb_action)

        # Memory & Settings Viewer
        settings_action = QAction("Memory & Settings Dashboard...", self)
        settings_action.triggered.connect(lambda: self.event_bus.emit(EventType.SETTINGS_REQUESTED))
        menu.addAction(settings_action)

        menu.addSeparator()

        # Exit
        exit_action = QAction("Exit IRIS", self)
        exit_action.triggered.connect(lambda: self.event_bus.emit(EventType.SYSTEM_SHUTDOWN))
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(EventType.STATE_CHANGED, self._on_state_changed)
        self.event_bus.subscribe(EventType.ORB_VISIBILITY_TOGGLED, self._on_orb_visibility)

    def _on_state_changed(self, event: Event) -> None:
        is_muted = self.state_manager.is_muted
        self.setIcon(QIcon(self._create_tray_pixmap(is_muted)))
        self.mute_action.setText("Unmute Microphone" if is_muted else "Mute Microphone")
        status_txt = "MUTED" if is_muted else self.state_manager.current_state.value.upper()
        self.setToolTip(f"IRIS Assistant [{status_txt}]")

    def _on_orb_visibility(self, event: Event) -> None:
        visible = event.data.get("visible", True)
        self.orb_action.setText("Hide Floating Orb" if visible else "Show Floating Orb")

    def _toggle_mute(self) -> None:
        self.state_manager.toggle_mute()

    def _toggle_orb(self) -> None:
        visible = self.state_manager.is_orb_visible
        self.state_manager.set_orb_visible(not visible)

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click shows orb if hidden, else opens settings
            if not self.state_manager.is_orb_visible:
                self.state_manager.set_orb_visible(True)
            else:
                self.event_bus.emit(EventType.SETTINGS_REQUESTED)
