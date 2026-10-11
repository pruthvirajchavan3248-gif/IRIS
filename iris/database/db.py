"""
IRIS Database Manager
Provides SQLite thread-safe operations, preference caching, history logging, and memory statistics.
"""

import sqlite3
import json
import csv
import io
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..core.config import get_config
from ..core.logger import get_logger
from .schema import CREATE_TABLES_SQL, DEFAULT_PREFERENCES, DEFAULT_APP_SHORTCUTS

logger = get_logger("database")


class DatabaseManager:
    """Thread-safe SQLite database manager for IRIS."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[Path] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._db_path = db_path or get_config().db_path
                cls._instance._local = threading.local()
                cls._instance._init_db()
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self._db_path),
                timeout=20.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for high concurrency and performance
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        """Creates tables and populates default settings and shortcuts if not already present."""
        conn = self._get_connection()
        try:
            with conn:
                conn.executescript(CREATE_TABLES_SQL)
                
                # Populate default preferences
                for key, val in DEFAULT_PREFERENCES.items():
                    conn.execute(
                        "INSERT OR IGNORE INTO user_preferences (key, value) VALUES (?, ?)",
                        (key, val)
                    )
                
                # Populate default app shortcuts
                for sc in DEFAULT_APP_SHORTCUTS:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO app_shortcuts 
                        (app_name, aliases, exe_path, launch_args, browser_url, is_enabled)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sc["app_name"],
                            sc["aliases"],
                            sc["exe_path"],
                            sc["launch_args"],
                            sc["browser_url"],
                            1
                        )
                    )
            logger.info(f"Database initialized successfully at {self._db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)

    # ------------------ Preferences ------------------ #
    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        conn = self._get_connection()
        cur = conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def set_preference(self, key: str, value: str) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO user_preferences (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
                """,
                (key, str(value))
            )

    def get_all_preferences(self) -> Dict[str, str]:
        conn = self._get_connection()
        cur = conn.execute("SELECT key, value FROM user_preferences")
        return {row["key"]: row["value"] for row in cur.fetchall()}

    # ------------------ App Shortcuts ------------------ #
    def get_all_shortcuts(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM app_shortcuts ORDER BY app_name ASC")
        return [dict(row) for row in cur.fetchall()]

    def find_shortcut(self, query: str) -> Optional[Dict[str, Any]]:
        """Finds matching app shortcut by name or alias."""
        clean_query = query.strip().lower()
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM app_shortcuts WHERE is_enabled = 1")
        for row in cur.fetchall():
            app_name = row["app_name"].lower()
            aliases = [a.strip().lower() for a in row["aliases"].split(",") if a.strip()]
            if clean_query == app_name or clean_query in aliases:
                return dict(row)
            # Partial match
            for alias in aliases:
                if alias in clean_query or clean_query in alias:
                    return dict(row)
        return None

    def upsert_shortcut(self, app_name: str, aliases: str, exe_path: str, launch_args: str = "", browser_url: str = "", is_enabled: int = 1) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO app_shortcuts (app_name, aliases, exe_path, launch_args, browser_url, is_enabled)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_name) DO UPDATE SET
                    aliases=excluded.aliases,
                    exe_path=excluded.exe_path,
                    launch_args=excluded.launch_args,
                    browser_url=excluded.browser_url,
                    is_enabled=excluded.is_enabled
                """,
                (app_name, aliases, exe_path, launch_args, browser_url, is_enabled)
            )

    def delete_shortcut(self, shortcut_id: int) -> bool:
        conn = self._get_connection()
        with conn:
            cur = conn.execute("DELETE FROM app_shortcuts WHERE id = ?", (shortcut_id,))
            return cur.rowcount > 0

    # ------------------ Conversation History ------------------ #
    def log_conversation(self, session_id: str, role: str, text: str, language: str = "hinglish", intent: str = "conversation") -> int:
        conn = self._get_connection()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO conversation_history (session_id, role, text, language, intent, timestamp)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (session_id, role, text, language, intent)
            )
            return cur.lastrowid

    def get_recent_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM conversation_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = [dict(r) for r in cur.fetchall()]
        rows.reverse()
        return rows

    # ------------------ Command History ------------------ #
    def log_command(self, utterance: str, intent: str, payload: Dict[str, Any], status: str, duration_ms: int = 0, error: str = "") -> int:
        conn = self._get_connection()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO command_history (user_utterance, resolved_intent, action_payload, execution_status, execution_time_ms, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (utterance, intent, json.dumps(payload), status, duration_ms, error)
            )
            return cur.lastrowid

    def get_recent_commands(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM command_history ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    # ------------------ Memory Management & Export ------------------ #
    def get_storage_stats(self) -> Dict[str, Any]:
        """Calculates storage footprint and row counts."""
        db_size_bytes = self._db_path.stat().st_size if self._db_path.exists() else 0
        conn = self._get_connection()
        
        counts = {}
        for table in ["user_preferences", "registered_projects", "app_shortcuts", "conversation_history", "command_history"]:
            try:
                cur = conn.execute(f"SELECT COUNT(*) as c FROM {table}")
                counts[table] = cur.fetchone()["c"]
            except Exception:
                counts[table] = 0
                
        return {
            "db_path": str(self._db_path),
            "size_bytes": db_size_bytes,
            "size_kb": round(db_size_bytes / 1024, 2),
            "size_mb": round(db_size_bytes / (1024 * 1024), 3),
            "row_counts": counts
        }

    def export_all_data(self) -> Dict[str, Any]:
        """Exports all database tables into a structured dictionary."""
        conn = self._get_connection()
        export = {
            "exported_at": datetime.now().isoformat(),
            "preferences": self.get_all_preferences(),
            "shortcuts": self.get_all_shortcuts(),
            "projects": [dict(r) for r in conn.execute("SELECT * FROM registered_projects").fetchall()],
            "conversation_history": [dict(r) for r in conn.execute("SELECT * FROM conversation_history").fetchall()],
            "command_history": [dict(r) for r in conn.execute("SELECT * FROM command_history").fetchall()]
        }
        return export

    def clear_history(self, clear_conversations: bool = True, clear_commands: bool = True) -> Tuple[int, int]:
        """Clears user conversations or command histories for privacy."""
        conn = self._get_connection()
        conv_deleted = 0
        cmd_deleted = 0
        with conn:
            if clear_conversations:
                cur = conn.execute("DELETE FROM conversation_history")
                conv_deleted = cur.rowcount
            if clear_commands:
                cur = conn.execute("DELETE FROM command_history")
                cmd_deleted = cur.rowcount
        try:
            conn.execute("VACUUM;")
        except Exception:
            pass
        return conv_deleted, cmd_deleted

    def close(self) -> None:
        """Closes thread-local database connection."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None


def get_db() -> DatabaseManager:
    return DatabaseManager()

