"""
IRIS Speech Subsystem
Handles Offline Wake-Word Detection, Multi-engine Speech-To-Text (Hindi, English, Hinglish),
Natural Edge-TTS Female Voice Generation, and Microphone Audio Loop.
"""

from .wake_word import WakeWordDetector
from .stt import SpeechToTextEngine
from .tts import TextToSpeechEngine
from .audio_manager import AudioManager

__all__ = [
    "WakeWordDetector",
    "SpeechToTextEngine",
    "TextToSpeechEngine",
    "AudioManager",
]
