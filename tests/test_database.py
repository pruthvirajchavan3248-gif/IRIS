"""
Unit Tests for IRIS SQLite Database & Memory Management
"""

import tempfile
import pytest
from pathlib import Path
from iris.database.db import DatabaseManager


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    # Re-instantiate database manager with isolated temporary DB
    DatabaseManager._instance = None
    db = DatabaseManager(db_path=db_path)
    yield db

    db.close()
    DatabaseManager._instance = None
    try:
        db_path.unlink(missing_ok=True)
    except Exception:
        pass



def test_db_initialization(temp_db):
    """Verifies default preferences and tables exist."""
    user_name = temp_db.get_preference("user_name")
    assert user_name == "Sir"
    
    shortcuts = temp_db.get_all_shortcuts()
    assert len(shortcuts) > 0
    names = [s["app_name"] for s in shortcuts]
    assert "chrome" in names
    assert "vscode" in names


def test_preferences_crud(temp_db):
    """Tests updating and retrieving user preferences."""
    temp_db.set_preference("user_name", "Alex")
    assert temp_db.get_preference("user_name") == "Alex"
    
    temp_db.set_preference("orb_theme", "cyber_purple")
    assert temp_db.get_preference("orb_theme") == "cyber_purple"


def test_shortcuts_search(temp_db):
    """Tests finding shortcuts by alias."""
    # "browser" is an alias for chrome
    match = temp_db.find_shortcut("browser")
    assert match is not None
    assert match["app_name"] == "chrome"

    # "vs code" alias for vscode
    match_code = temp_db.find_shortcut("vs code")
    assert match_code is not None
    assert match_code["app_name"] == "vscode"


def test_conversation_logging(temp_db):
    """Tests conversation history storage and retrieval."""
    temp_db.log_conversation("sess-1", "user", "Hello IRIS", "en", "greeting")
    temp_db.log_conversation("sess-1", "iris", "Hello Sir!", "en", "greeting")

    convs = temp_db.get_recent_conversations(limit=10)
    assert len(convs) == 2
    assert convs[0]["text"] == "Hello IRIS"
    assert convs[1]["text"] == "Hello Sir!"


def test_command_history_and_stats(temp_db):
    """Tests logging commands, stats calculation, and export."""
    temp_db.log_command("Chrome kholo", "app_launch", {"app": "chrome"}, "SUCCESS", 120)
    
    stats = temp_db.get_storage_stats()
    assert stats["row_counts"]["command_history"] >= 1
    assert stats["size_bytes"] > 0

    exported = temp_db.export_all_data()
    assert "preferences" in exported
    assert "conversation_history" in exported
    assert len(exported["command_history"]) >= 1


def test_clear_history_privacy(temp_db):
    """Tests privacy clearance of conversations and command history."""
    temp_db.log_conversation("sess-1", "user", "Private message")
    temp_db.log_command("Sensitive task", "test", {}, "SUCCESS")

    conv_del, cmd_del = temp_db.clear_history()
    assert conv_del >= 1
    assert cmd_del >= 1
    assert len(temp_db.get_recent_conversations()) == 0
    assert len(temp_db.get_recent_commands()) == 0
