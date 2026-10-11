"""
IRIS Database and Memory Management
Local SQLite store for user preferences, project registry, app shortcuts, conversation history, and voice configurations.
"""

from .db import DatabaseManager, get_db
from .project_registry import ProjectRegistry, ProjectInfo

__all__ = [
    "DatabaseManager",
    "get_db",
    "ProjectRegistry",
    "ProjectInfo",
]
