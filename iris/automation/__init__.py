"""
IRIS Automation Subsystem
Controls Windows applications, executes authorized voice commands,
handles dictation typing, browser automation, and registered project execution.
"""

from .windows_controller import WindowsController
from .dictation import DictationManager
from .browser_controller import BrowserController
from .project_runner import ProjectRunner
from .security import SecurityGuard

__all__ = [
    "WindowsController",
    "DictationManager",
    "BrowserController",
    "ProjectRunner",
    "SecurityGuard",
]
