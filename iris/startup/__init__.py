"""
IRIS Windows Startup Configuration Module
Configures silent background autostart after Windows login without console window.
"""

from .windows_startup import WindowsStartupManager

__all__ = ["WindowsStartupManager"]
