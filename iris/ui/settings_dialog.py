"""
IRIS Settings & Database Memory Viewer Dialog
Modern dark glassmorphic interface for inspecting SQLite records, managing developer projects,
controlling voice parameters, and configuring Windows startup.
"""

import sys
import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QTextEdit,
    QSplitter,
)

from ..core.config import get_config
from ..core.logger import get_logger
from ..database.db import get_db
from ..database.project_registry import ProjectRegistry
from ..speech.tts import TextToSpeechEngine

logger = get_logger("settings_dialog")


class SettingsAndDatabaseViewer(QDialog):
    """Main Settings and Database Memory Viewer for IRIS."""

    DARK_STYLE = """
    QDialog {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Segoe UI', sans-serif;
    }
    QTabWidget::pane {
        border: 1px solid #1e293b;
        background-color: #0f172a;
        border-radius: 8px;
    }
    QTabBar::tab {
        background: #1e293b;
        color: #94a3b8;
        padding: 10px 22px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
        font-weight: 600;
        font-size: 13px;
    }
    QTabBar::tab:selected {
        background: #0284c7;
        color: #ffffff;
    }
    QTabBar::tab:hover:!selected {
        background: #334155;
        color: #e2e8f0;
    }
    QLabel {
        color: #cbd5e1;
        font-size: 13px;
    }
    QLineEdit, QComboBox, QTextEdit {
        background-color: #1e293b;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
        border: 1px solid #38bdf8;
    }
    QPushButton {
        background-color: #0284c7;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 8px 18px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #0369a1;
    }
    QPushButton:pressed {
        background-color: #0c4a6e;
    }
    QPushButton#dangerBtn {
        background-color: #dc2626;
    }
    QPushButton#dangerBtn:hover {
        background-color: #b91c1c;
    }
    QPushButton#secondaryBtn {
        background-color: #334155;
    }
    QPushButton#secondaryBtn:hover {
        background-color: #475569;
    }
    QTableWidget {
        background-color: #1e293b;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 6px;
        gridline-color: #334155;
        font-size: 12px;
    }
    QHeaderView::section {
        background-color: #0f172a;
        color: #38bdf8;
        padding: 6px;
        border: 1px solid #334155;
        font-weight: bold;
    }
    QGroupBox {
        border: 1px solid #334155;
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 14px;
        font-weight: bold;
        color: #38bdf8;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
    }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.db = get_db()
        self.project_registry = ProjectRegistry()
        self.tts = TextToSpeechEngine()

        self.setWindowTitle("IRIS Virtual Assistant — Memory & Settings Dashboard")
        self.resize(960, 680)
        self.setStyleSheet(self.DARK_STYLE)

        self._setup_ui()
        self._load_settings()
        self._refresh_db_stats()
        self._load_table_data("conversation_history")

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title
        header_layout = QHBoxLayout()
        title_label = QLabel("IRIS (Intelligent Responsive Interactive System)")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #38bdf8;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.stat_label = QLabel("Storage: Calculating...")
        self.stat_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        header_layout.addWidget(self.stat_label)
        main_layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_db = QWidget()
        self.tab_projects = QWidget()
        self.tab_shortcuts = QWidget()
        self.tab_voice = QWidget()
        self.tab_general = QWidget()

        self.tabs.addTab(self.tab_db, "Memory & Database")
        self.tabs.addTab(self.tab_projects, "Project Registry")
        self.tabs.addTab(self.tab_shortcuts, "App Shortcuts")
        self.tabs.addTab(self.tab_voice, "Voice & Audio")
        self.tabs.addTab(self.tab_general, "General & Security")

        self._setup_tab_db()
        self._setup_tab_projects()
        self._setup_tab_shortcuts()
        self._setup_tab_voice()
        self._setup_tab_general()

        main_layout.addWidget(self.tabs)

        # Bottom Action Bar
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        bottom_layout.addWidget(save_btn)

        main_layout.addLayout(bottom_layout)

    # ---------------- TAB 1: Database & Memory Viewer ---------------- #
    def _setup_tab_db(self) -> None:
        layout = QVBoxLayout(self.tab_db)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Controls bar
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Table:"))
        
        self.table_selector = QComboBox()
        self.table_selector.addItems([
            "conversation_history",
            "command_history",
            "registered_projects",
            "app_shortcuts",
            "user_preferences"
        ])
        self.table_selector.currentTextChanged.connect(self._load_table_data)
        top_bar.addWidget(self.table_selector)

        top_bar.addWidget(QLabel("Search:"))
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Filter rows...")
        self.search_filter.textChanged.connect(self._filter_table_rows)
        top_bar.addWidget(self.search_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(lambda: self._load_table_data(self.table_selector.currentText()))
        top_bar.addWidget(refresh_btn)

        top_bar.addStretch()

        export_btn = QPushButton("Export Memory (JSON)")
        export_btn.clicked.connect(self._export_memory)
        top_bar.addWidget(export_btn)

        clear_btn = QPushButton("Clear History")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self._clear_history_prompt)
        top_bar.addWidget(clear_btn)

        layout.addLayout(top_bar)

        # Table Viewer
        self.db_table = QTableWidget()
        self.db_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.db_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.db_table)

    def _refresh_db_stats(self) -> None:
        stats = self.db.get_storage_stats()
        self.stat_label.setText(f"Database: {stats['size_kb']} KB | Total Records: {sum(stats['row_counts'].values())}")

    def _load_table_data(self, table_name: str) -> None:
        self._refresh_db_stats()
        conn = self.db._get_connection()
        try:
            cur = conn.execute(f"SELECT * FROM {table_name} ORDER BY 1 DESC LIMIT 300")
            rows = cur.fetchall()
            if not rows:
                self.db_table.clear()
                self.db_table.setRowCount(0)
                self.db_table.setColumnCount(0)
                return

            columns = [desc[0] for desc in cur.description]
            self.db_table.clear()
            self.db_table.setColumnCount(len(columns))
            self.db_table.setHorizontalHeaderLabels(columns)
            self.db_table.setRowCount(len(rows))

            for r_idx, row in enumerate(rows):
                for c_idx, col in enumerate(columns):
                    val = str(row[col]) if row[col] is not None else ""
                    item = QTableWidgetItem(val)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.db_table.setItem(r_idx, c_idx, item)

        except Exception as e:
            logger.error(f"Error loading table {table_name}: {e}")

    def _filter_table_rows(self, query: str) -> None:
        clean = query.strip().lower()
        for r in range(self.db_table.rowCount()):
            match = False
            for c in range(self.db_table.columnCount()):
                item = self.db_table.item(r, c)
                if item and clean in item.text().lower():
                    match = True
                    break
            self.db_table.setRowHidden(r, not match and len(clean) > 0)

    def _export_memory(self) -> None:
        save_path, _ = QFileDialog.getSaveFileName(self, "Export IRIS Memory", "iris_memory_export.json", "JSON Files (*.json)")
        if save_path:
            data = self.db.export_all_data()
            Path(save_path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            QMessageBox.information(self, "Export Successful", f"Memory database exported to:\n{save_path}")

    def _clear_history_prompt(self) -> None:
        res = QMessageBox.warning(
            self,
            "Clear History Confirmation",
            "Are you sure you want to delete conversation and command histories?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            conv_del, cmd_del = self.db.clear_history()
            self._load_table_data(self.table_selector.currentText())
            QMessageBox.information(self, "History Cleared", f"Deleted {conv_del} conversations and {cmd_del} commands.")

    # ---------------- TAB 2: Project Registry ---------------- #
    def _setup_tab_projects(self) -> None:
        layout = QVBoxLayout(self.tab_projects)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Form
        group = QGroupBox("Register / Update Developer Project")
        form = QFormLayout(group)

        self.proj_name_input = QLineEdit()
        self.proj_name_input.setPlaceholderText("e.g. Level Up, Portfolio, Microservice")
        form.addRow("Project Name:", self.proj_name_input)

        path_box = QHBoxLayout()
        self.proj_path_input = QLineEdit()
        self.proj_path_input.setPlaceholderText("C:/Users/.../MyProject")
        path_box.addWidget(self.proj_path_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.clicked.connect(self._browse_project_path)
        path_box.addWidget(browse_btn)

        detect_btn = QPushButton("Auto-Detect Stack")
        detect_btn.setObjectName("secondaryBtn")
        detect_btn.clicked.connect(self._auto_detect_project_stack)
        path_box.addWidget(detect_btn)
        form.addRow("Directory Path:", path_box)

        self.proj_tech_input = QLineEdit()
        self.proj_tech_input.setPlaceholderText("e.g. Node.js, Python, Rust (Cargo), React")
        form.addRow("Tech Stack:", self.proj_tech_input)

        self.proj_cmd_input = QLineEdit()
        self.proj_cmd_input.setPlaceholderText("e.g. npm run dev, python main.py, cargo run")
        form.addRow("Approved Run Command:", self.proj_cmd_input)

        btn_box = QHBoxLayout()
        save_proj_btn = QPushButton("Save Project to Registry")
        save_proj_btn.clicked.connect(self._save_project)
        btn_box.addWidget(save_proj_btn)

        del_proj_btn = QPushButton("Delete Selected Project")
        del_proj_btn.setObjectName("dangerBtn")
        del_proj_btn.clicked.connect(self._delete_project)
        btn_box.addWidget(del_proj_btn)
        form.addRow("", btn_box)

        layout.addWidget(group)

        # Registered projects table
        self.projects_table = QTableWidget()
        self.projects_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.projects_table.horizontalHeader().setStretchLastSection(True)
        self.projects_table.cellClicked.connect(self._on_project_table_clicked)
        layout.addWidget(self.projects_table)

        self._refresh_projects_table()

    def _browse_project_path(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Project Root Folder")
        if folder:
            self.proj_path_input.setText(folder)
            if not self.proj_name_input.text().strip():
                self.proj_name_input.setText(Path(folder).name)
            self._auto_detect_project_stack()

    def _auto_detect_project_stack(self) -> None:
        p_str = self.proj_path_input.text().strip()
        if p_str:
            p = Path(p_str)
            tech = self.project_registry.detect_tech_stack(p)
            cmd = self.project_registry.suggest_default_run_command(tech, p)
            self.proj_tech_input.setText(tech)
            self.proj_cmd_input.setText(cmd)

    def _save_project(self) -> None:
        name = self.proj_name_input.text().strip()
        path_str = self.proj_path_input.text().strip()
        cmd = self.proj_cmd_input.text().strip()

        if not name or not path_str:
            QMessageBox.warning(self, "Validation Error", "Project name and path are required.")
            return

        try:
            self.project_registry.register_project(name, path_str, cmd)
            self._refresh_projects_table()
            QMessageBox.information(self, "Saved", f"Project '{name}' registered successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save project: {e}")

    def _delete_project(self) -> None:
        row = self.projects_table.currentRow()
        if row >= 0:
            p_id = int(self.projects_table.item(row, 0).text())
            name = self.projects_table.item(row, 1).text()
            self.project_registry.delete_project(p_id)
            self._refresh_projects_table()
            QMessageBox.information(self, "Deleted", f"Project '{name}' removed from registry.")

    def _refresh_projects_table(self) -> None:
        projects = self.project_registry.get_all_projects()
        cols = ["ID", "Name", "Path", "Tech Stack", "Run Command", "Last Opened"]
        self.projects_table.clear()
        self.projects_table.setColumnCount(len(cols))
        self.projects_table.setHorizontalHeaderLabels(cols)
        self.projects_table.setRowCount(len(projects))

        for r, p in enumerate(projects):
            self.projects_table.setItem(r, 0, QTableWidgetItem(str(p.id)))
            self.projects_table.setItem(r, 1, QTableWidgetItem(p.name))
            self.projects_table.setItem(r, 2, QTableWidgetItem(p.path))
            self.projects_table.setItem(r, 3, QTableWidgetItem(p.tech_stack))
            self.projects_table.setItem(r, 4, QTableWidgetItem(p.run_command))
            self.projects_table.setItem(r, 5, QTableWidgetItem(str(p.last_opened or "")))

    def _on_project_table_clicked(self, row: int, col: int) -> None:
        self.proj_name_input.setText(self.projects_table.item(row, 1).text())
        self.proj_path_input.setText(self.projects_table.item(row, 2).text())
        self.proj_tech_input.setText(self.projects_table.item(row, 3).text())
        self.proj_cmd_input.setText(self.projects_table.item(row, 4).text())

    # ---------------- TAB 3: App Shortcuts ---------------- #
    def _setup_tab_shortcuts(self) -> None:
        layout = QVBoxLayout(self.tab_shortcuts)
        layout.setContentsMargins(14, 14, 14, 14)
        
        group = QGroupBox("Add / Edit Application Shortcut")
        form = QFormLayout(group)

        self.sc_name = QLineEdit()
        self.sc_name.setPlaceholderText("e.g. spotify, figma")
        form.addRow("App Name:", self.sc_name)

        self.sc_aliases = QLineEdit()
        self.sc_aliases.setPlaceholderText("e.g. music, gana, player")
        form.addRow("Aliases (comma separated):", self.sc_aliases)

        sc_path_box = QHBoxLayout()
        self.sc_exe = QLineEdit()
        self.sc_exe.setPlaceholderText("C:/Program Files/.../app.exe")
        sc_path_box.addWidget(self.sc_exe)
        sc_browse = QPushButton("Browse...")
        sc_browse.setObjectName("secondaryBtn")
        sc_browse.clicked.connect(self._browse_shortcut_exe)
        sc_path_box.addWidget(sc_browse)
        form.addRow("Executable Path:", sc_path_box)

        self.sc_url = QLineEdit()
        self.sc_url.setPlaceholderText("https://... (Optional web fallback)")
        form.addRow("Browser URL:", self.sc_url)

        save_sc_btn = QPushButton("Save Shortcut")
        save_sc_btn.clicked.connect(self._save_shortcut)
        form.addRow("", save_sc_btn)

        layout.addWidget(group)

        self.sc_table = QTableWidget()
        self.sc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.sc_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.sc_table)

        self._refresh_shortcuts_table()

    def _browse_shortcut_exe(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Select Executable", "", "Executables (*.exe);;All Files (*.*)")
        if file:
            self.sc_exe.setText(file)

    def _save_shortcut(self) -> None:
        name = self.sc_name.text().strip()
        aliases = self.sc_aliases.text().strip()
        exe = self.sc_exe.text().strip()
        url = self.sc_url.text().strip()

        if not name:
            QMessageBox.warning(self, "Validation", "App name is required.")
            return

        self.db.upsert_shortcut(name, aliases, exe, browser_url=url)
        self._refresh_shortcuts_table()
        QMessageBox.information(self, "Saved", f"Shortcut '{name}' saved.")

    def _refresh_shortcuts_table(self) -> None:
        shortcuts = self.db.get_all_shortcuts()
        cols = ["ID", "App Name", "Aliases", "Executable Path", "Browser URL"]
        self.sc_table.clear()
        self.sc_table.setColumnCount(len(cols))
        self.sc_table.setHorizontalHeaderLabels(cols)
        self.sc_table.setRowCount(len(shortcuts))

        for r, sc in enumerate(shortcuts):
            self.sc_table.setItem(r, 0, QTableWidgetItem(str(sc["id"])))
            self.sc_table.setItem(r, 1, QTableWidgetItem(sc["app_name"]))
            self.sc_table.setItem(r, 2, QTableWidgetItem(sc["aliases"]))
            self.sc_table.setItem(r, 3, QTableWidgetItem(sc["exe_path"]))
            self.sc_table.setItem(r, 4, QTableWidgetItem(sc["browser_url"]))

    # ---------------- TAB 4: Voice & Audio ---------------- #
    def _setup_tab_voice(self) -> None:
        layout = QVBoxLayout(self.tab_voice)
        layout.setContentsMargins(14, 14, 14, 14)

        group = QGroupBox("Natural Female Voice Settings (Edge-TTS)")
        form = QFormLayout(group)

        self.voice_hi_combo = QComboBox()
        self.voice_hi_combo.addItems(["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"])
        form.addRow("Hindi / Hinglish Voice:", self.voice_hi_combo)

        self.voice_en_combo = QComboBox()
        self.voice_en_combo.addItems(["en-IN-NeerjaNeural", "en-IN-AnanyaNeural", "en-US-JennyNeural"])
        form.addRow("English Voice:", self.voice_en_combo)

        self.speech_rate_combo = QComboBox()
        self.speech_rate_combo.addItems(["-10%", "+0%", "+10%", "+20%"])
        form.addRow("Speaking Rate:", self.speech_rate_combo)

        test_speech_box = QHBoxLayout()
        test_btn = QPushButton("Test Hindi Greeting")
        test_btn.clicked.connect(lambda: self.tts.speak("Ji Sir, IRIS ready hai. Main aapki kya madad kar sakti hoon?", block=False))
        test_speech_box.addWidget(test_btn)

        test_en_btn = QPushButton("Test English Greeting")
        test_en_btn.setObjectName("secondaryBtn")
        test_en_btn.clicked.connect(lambda: self.tts.speak("Hello Sir, IRIS is active and ready for your commands.", block=False))
        test_speech_box.addWidget(test_en_btn)
        form.addRow("Voice Preview:", test_speech_box)

        layout.addWidget(group)

        stt_group = QGroupBox("Microphone & Speech Recognition")
        stt_form = QFormLayout(stt_group)

        self.stt_engine_combo = QComboBox()
        self.stt_engine_combo.addItems(["speech_recognition (Google / Offline fallback)", "vosk (Offline)", "faster_whisper"])
        stt_form.addRow("STT Recognition Engine:", self.stt_engine_combo)

        layout.addWidget(stt_group)
        layout.addStretch()

    # ---------------- TAB 5: General & Security ---------------- #
    def _setup_tab_general(self) -> None:
        layout = QVBoxLayout(self.tab_general)
        layout.setContentsMargins(14, 14, 14, 14)

        group = QGroupBox("Google Gemini AI Integration")
        form = QFormLayout(group)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter Google Gemini API Key")
        form.addRow("Gemini API Key:", self.api_key_input)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"])
        form.addRow("Primary AI Model:", self.model_combo)

        layout.addWidget(group)

        sys_group = QGroupBox("User Preferences & Windows Startup")
        sys_form = QFormLayout(sys_group)

        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("Sir")
        sys_form.addRow("Preferred Salutation / Name:", self.user_name_input)

        self.auto_start_check = QCheckBox("Start IRIS automatically on Windows login (Background mode without terminal)")
        sys_form.addRow("", self.auto_start_check)

        self.confirm_check = QCheckBox("Require voice confirmation before executing high-risk system commands")
        sys_form.addRow("", self.confirm_check)

        layout.addWidget(sys_group)
        layout.addStretch()

    def _load_settings(self) -> None:
        self.user_name_input.setText(self.db.get_preference("user_name", "Sir"))
        self.api_key_input.setText(self.config.gemini_api_key)
        self.voice_hi_combo.setCurrentText(self.db.get_preference("voice_hi", "hi-IN-SwaraNeural"))
        self.voice_en_combo.setCurrentText(self.db.get_preference("voice_en", "en-IN-NeerjaNeural"))
        self.speech_rate_combo.setCurrentText(self.db.get_preference("voice_rate", "+0%"))
        self.auto_start_check.setChecked(self.db.get_preference("auto_start_enabled", "true") == "true")
        self.confirm_check.setChecked(self.db.get_preference("confirmation_required", "true") == "true")

    def _save_settings(self) -> None:
        self.db.set_preference("user_name", self.user_name_input.text().strip() or "Sir")
        self.db.set_preference("voice_hi", self.voice_hi_combo.currentText())
        self.db.set_preference("voice_en", self.voice_en_combo.currentText())
        self.db.set_preference("voice_rate", self.speech_rate_combo.currentText())
        self.db.set_preference("auto_start_enabled", "true" if self.auto_start_check.isChecked() else "false")
        self.db.set_preference("confirmation_required", "true" if self.confirm_check.isChecked() else "false")
        
        # Save API key to .env if provided
        key = self.api_key_input.text().strip()
        if key:
            env_file = self.config.base_dir / ".env"
            lines = []
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if not line.startswith("GEMINI_API_KEY="):
                        lines.append(line)
            lines.append(f"GEMINI_API_KEY={key}")
            env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.config.gemini_api_key = key

        QMessageBox.information(self, "Settings Saved", "Preferences and configurations saved successfully.")
