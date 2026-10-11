"""
IRIS Configuration Module
Handles environment variables, paths, and application settings.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any
from dotenv import load_dotenv

# Base Directories
APP_DIR = Path(__file__).resolve().parent.parent.parent
IRIS_PKG_DIR = Path(__file__).resolve().parent.parent
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "IRIS_Assistant"
LOGS_DIR = USER_DATA_DIR / "logs"
DB_DIR = USER_DATA_DIR / "data"
TEMP_AUDIO_DIR = USER_DATA_DIR / "temp_audio"

for directory in [USER_DATA_DIR, LOGS_DIR, DB_DIR, TEMP_AUDIO_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Load .env file from app directory
ENV_FILE = APP_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)
else:
    load_dotenv()


@dataclass
class Config:
    # General
    app_name: str = "IRIS Virtual Assistant"
    app_version: str = "1.0.0"
    user_name: str = os.getenv("IRIS_USER_NAME", "Sir")
    log_level: str = os.getenv("IRIS_LOG_LEVEL", "INFO")
    
    # Paths
    base_dir: Path = APP_DIR
    data_dir: Path = DB_DIR
    logs_dir: Path = LOGS_DIR
    temp_audio_dir: Path = TEMP_AUDIO_DIR
    db_path: Path = DB_DIR / "iris_memory.db"
    
    # Gemini AI
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    gemini_fallback_model: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    ai_temperature: float = float(os.getenv("IRIS_AI_TEMPERATURE", "0.5"))
    max_tokens: int = int(os.getenv("IRIS_MAX_TOKENS", "512"))
    
    # Speech Recognition (STT)
    stt_engine: str = os.getenv("IRIS_STT_ENGINE", "speech_recognition")  # "faster_whisper", "vosk", "speech_recognition"
    whisper_model_size: str = os.getenv("IRIS_WHISPER_MODEL", "base")
    whisper_device: str = os.getenv("IRIS_WHISPER_DEVICE", "cpu")
    microphone_index: int = int(os.getenv("IRIS_MIC_INDEX", "-1"))
    sample_rate: int = 16000
    energy_threshold: int = int(os.getenv("IRIS_ENERGY_THRESHOLD", "700"))
    dynamic_energy_threshold: bool = True
    silence_timeout: float = float(os.getenv("IRIS_SILENCE_TIMEOUT", "0.6"))
    phrase_time_limit: float = float(os.getenv("IRIS_PHRASE_LIMIT", "7.0"))
    
    # Wake Words & Wake Phrases
    wake_phrases: List[str] = field(default_factory=lambda: [
        "hello iris",
        "hey iris",
        "utha jao iris",
        "uth jao iris",
        "iris",
        "wake up iris",
        "ok iris",
        "sun rahi ho iris"
    ])
    
    # Text-to-Speech (TTS)
    tts_engine: str = os.getenv("IRIS_TTS_ENGINE", "edge_tts")  # "edge_tts", "pyttsx3"
    edge_voice_hi: str = os.getenv("IRIS_VOICE_HI", "hi-IN-SwaraNeural")
    edge_voice_en: str = os.getenv("IRIS_VOICE_EN", "en-IN-NeerjaNeural")
    edge_voice_us: str = os.getenv("IRIS_VOICE_US", "en-US-JennyNeural")
    tts_rate: str = os.getenv("IRIS_TTS_RATE", "+15%")
    tts_pitch: str = os.getenv("IRIS_TTS_PITCH", "+0Hz")
    pyttsx3_voice_id: str = os.getenv("IRIS_PYTTSX3_VOICE_ID", "")
    
    # UI Floating Orb Settings
    orb_size: int = int(os.getenv("IRIS_ORB_SIZE", "130"))
    orb_start_x: int = int(os.getenv("IRIS_ORB_START_X", "-1"))
    orb_start_y: int = int(os.getenv("IRIS_ORB_START_Y", "-1"))
    orb_always_on_top: bool = True
    orb_opacity: float = float(os.getenv("IRIS_ORB_OPACITY", "0.95"))
    orb_theme: str = os.getenv("IRIS_ORB_THEME", "cyber_cyan")
    
    # Security & Execution Guard
    require_confirmation_for_destructive: bool = os.getenv("IRIS_REQUIRE_CONFIRMATION", "true").lower() == "true"
    allowed_file_extensions: List[str] = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".html", ".css", ".rs", ".go", ".cpp", ".c", ".java", ".json", ".txt", ".md"
    ])
    
    # System Shortcuts / Known Programs
    app_mappings: Dict[str, List[str]] = field(default_factory=lambda: {
        "chrome": ["chrome.exe", "google chrome"],
        "brave": ["brave.exe", "brave"],
        "edge": ["msedge.exe", "microsoft edge"],
        "firefox": ["firefox.exe", "mozilla firefox"],
        "vscode": ["code.exe", "visual studio code"],
        "whatsapp": ["WhatsApp.exe", "whatsapp"],
        "notepad": ["notepad.exe", "notepad"],
        "calculator": ["calc.exe", "calculator"],
        "explorer": ["explorer.exe", "file explorer"],
        "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
        "spotify": ["spotify.exe", "spotify"],
        "word": ["winword.exe", "microsoft word"],
        "excel": ["excel.exe", "microsoft excel"],
    })


_config_instance: Config = None


def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
