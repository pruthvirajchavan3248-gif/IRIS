"""
IRIS Database Schema Definitions
"""

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registered_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,
    tech_stack TEXT NOT NULL,
    run_command TEXT NOT NULL,
    test_command TEXT DEFAULT '',
    build_command TEXT DEFAULT '',
    last_opened TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS app_shortcuts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT UNIQUE NOT NULL,
    aliases TEXT NOT NULL, -- Comma-separated alias list e.g. "chrome,google chrome,browser"
    exe_path TEXT NOT NULL,
    launch_args TEXT DEFAULT '',
    browser_url TEXT DEFAULT '',
    is_enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL, -- "user" | "iris" | "system"
    text TEXT NOT NULL,
    language TEXT DEFAULT 'hinglish',
    intent TEXT DEFAULT 'conversation',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_utterance TEXT NOT NULL,
    resolved_intent TEXT NOT NULL,
    action_payload TEXT,
    execution_status TEXT NOT NULL, -- "SUCCESS" | "FAILED" | "CONFIRMATION_REJECTED" | "SECURITY_BLOCKED"
    execution_time_ms INTEGER DEFAULT 0,
    error_message TEXT DEFAULT '',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conv_session ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_proj_name ON registered_projects(name);
CREATE INDEX IF NOT EXISTS idx_app_name ON app_shortcuts(app_name);
"""

DEFAULT_PREFERENCES = {
    "user_name": "Sir",
    "language": "hinglish",
    "tts_engine": "edge_tts",
    "voice_hi": "hi-IN-SwaraNeural",
    "voice_en": "en-IN-NeerjaNeural",
    "voice_us": "en-US-JennyNeural",
    "voice_rate": "+0%",
    "voice_pitch": "+0Hz",
    "orb_size": "130",
    "orb_x": "1720",
    "orb_y": "860",
    "orb_theme": "cyber_cyan",
    "orb_opacity": "0.95",
    "auto_start_enabled": "true",
    "mic_muted": "false",
    "confirmation_required": "true",
    "stt_engine": "vosk"
}

DEFAULT_APP_SHORTCUTS = [
    {
        "app_name": "chrome",
        "aliases": "chrome,google chrome,browser",
        "exe_path": "chrome.exe",
        "launch_args": "",
        "browser_url": ""
    },
    {
        "app_name": "vscode",
        "aliases": "code,vs code,visual studio code,editor",
        "exe_path": "code.exe",
        "launch_args": "",
        "browser_url": ""
    },
    {
        "app_name": "whatsapp",
        "aliases": "whatsapp,wa",
        "exe_path": "WhatsApp.exe",
        "launch_args": "",
        "browser_url": "https://web.whatsapp.com"
    },
    {
        "app_name": "notepad",
        "aliases": "notepad,text editor",
        "exe_path": "notepad.exe",
        "launch_args": "",
        "browser_url": ""
    },
    {
        "app_name": "calculator",
        "aliases": "calculator,calc,hisab",
        "exe_path": "calc.exe",
        "launch_args": "",
        "browser_url": ""
    },
    {
        "app_name": "explorer",
        "aliases": "explorer,files,my computer,file manager",
        "exe_path": "explorer.exe",
        "launch_args": "",
        "browser_url": ""
    },
    {
        "app_name": "youtube",
        "aliases": "youtube,yt",
        "exe_path": "",
        "launch_args": "",
        "browser_url": "https://www.youtube.com"
    },
    {
        "app_name": "chatgpt",
        "aliases": "chatgpt,chat gpt,openai",
        "exe_path": "",
        "launch_args": "",
        "browser_url": "https://chatgpt.com"
    }
]
