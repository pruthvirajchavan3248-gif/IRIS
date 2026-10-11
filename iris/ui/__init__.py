"""
IRIS User Interface Subsystem
Futuristic Floating Holographic AI Orb, Modern Glassmorphism Settings & Database Viewer,
and Windows System Tray integration.
"""

from .orb_window import FloatingOrbWindow
from .settings_dialog import SettingsAndDatabaseViewer
from .tray_icon import IrisTrayIcon

__all__ = [
    "FloatingOrbWindow",
    "SettingsAndDatabaseViewer",
    "IrisTrayIcon",
]
