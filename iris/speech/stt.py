"""
IRIS Speech-To-Text (STT) Subsystem
Supports Hindi, English, and Hinglish with optimized fast recognition.
Includes dynamic noise reduction, energy threshold auto-calibration, and language detection.
"""

import io
import wave
import threading
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

from ..core.config import get_config
from ..core.logger import get_logger

logger = get_logger("stt")


class SpeechToTextEngine:
    """Multi-backend Speech-To-Text processor."""

    def __init__(self):
        self.config = get_config()
        self._whisper_model = None
        self._vosk_model = None
        self._recognizer = None
        self._lock = threading.Lock()
        self._init_recognizer()

    def _init_recognizer(self) -> None:
        """Initializes python speech_recognition module with optimized timeouts."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.config.energy_threshold
            self._recognizer.dynamic_energy_threshold = self.config.dynamic_energy_threshold
            self._recognizer.pause_threshold = self.config.silence_timeout
            self._recognizer.non_speaking_duration = 0.25
            # Fast operation timeout to prevent hanging on network delays
            self._recognizer.operation_timeout = 2.5
            logger.info("SpeechRecognition backend initialized.")
        except ImportError:
            logger.warning("speech_recognition package not installed yet.")

    def calibrate_ambient_noise(self, source, duration: float = 1.0) -> None:
        """Calibrates microphone against background room noise."""
        if self._recognizer:
            try:
                logger.info(f"Calibrating ambient noise for {duration} seconds...")
                self._recognizer.adjust_for_ambient_noise(source, duration=duration)
                logger.info(f"Calibrated energy threshold: {self._recognizer.energy_threshold:.1f}")
            except Exception as e:
                logger.warning(f"Noise calibration error: {e}")

    def transcribe_audio_data(self, audio_data, preferred_language: Optional[str] = None, is_wake_word_check: bool = False) -> Tuple[str, str]:
        """
        Transcribes speech recognition AudioData instance.
        If is_wake_word_check is True, performs a single fast pass on 'en-IN' without retrying
        multiple languages to eliminate latency on idle silence/noise.
        Returns:
            (transcribed_text, detected_language)
        """
        if not self._recognizer or not audio_data:
            return "", "en"

        text = ""

        # Fast pass for wake-word checking:
        # 'en-IN' is remarkably accurate for Hindi/Hinglish greetings ("hello iris", "hey iris", "uth jao iris")
        if is_wake_word_check:
            try:
                text = self._recognizer.recognize_google(audio_data, language="en-IN")
                if text and len(text.strip()) > 0:
                    detected_lang = self._detect_language_heuristic(text)
                    return text.strip(), detected_lang
            except Exception:
                # Normal UnknownValueError or RequestError when silence/noise — return empty fast
                return "", "unknown"
            return "", "unknown"

        # Active command phase: try 'en-IN' first (covers 95% of Hinglish/English desktop commands)
        target_lang_codes = ["en-IN", "hi-IN"]

        for code in target_lang_codes:
            try:
                text = self._recognizer.recognize_google(audio_data, language=code)
                if text and len(text.strip()) > 0:
                    detected_lang = self._detect_language_heuristic(text)
                    logger.info(f"Transcribed [{code} -> {detected_lang}]: '{text}'")
                    return text.strip(), detected_lang
            except Exception:
                continue

        # Optional Faster-Whisper Fallback if available
        if self._whisper_model is not None:
            try:
                wav_bytes = audio_data.get_wav_data()
                text, detected_lang = self._transcribe_with_whisper(wav_bytes)
                if text:
                    return text, detected_lang
            except Exception as e:
                logger.warning(f"Faster-whisper fallback failed: {e}")

        # Optional Vosk Fallback if available
        if self._vosk_model is not None:
            try:
                wav_bytes = audio_data.get_wav_data()
                text, detected_lang = self._transcribe_with_vosk(wav_bytes)
                if text:
                    return text, detected_lang
            except Exception as e:
                logger.warning(f"Vosk fallback failed: {e}")

        return "", "unknown"

    def transcribe_audio_file(self, file_path: Path, preferred_language: Optional[str] = None) -> Tuple[str, str]:
        """Transcribes a WAV file from disk."""
        if not self._recognizer:
            return "", "unknown"
        try:
            import speech_recognition as sr
            with sr.AudioFile(str(file_path)) as source:
                audio = self._recognizer.record(source)
                return self.transcribe_audio_data(audio, preferred_language)
        except Exception as e:
            logger.error(f"Error reading audio file {file_path}: {e}")
            return "", "error"

    @staticmethod
    def _detect_language_heuristic(text: str) -> str:
        """
        Heuristic language identifier for Hindi, English, and Hinglish.
        Detects Devanagari Unicode range, Hinglish lexical markers, or English words.
        """
        if not text:
            return "en"

        # Check for Devanagari Unicode range (U+0900 to U+097F)
        devanagari_count = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
        if devanagari_count > len(text) * 0.2:
            return "hi"

        # Common Hinglish conversational marker words
        hinglish_words = {
            "kholo", "band", "karo", "chalao", "batao", "samjhao", "kaise", "kya", "kyun",
            "mera", "meri", "mere", "aap", "tum", "main", "hum", "yeh", "woh", "hai",
            "hain", "tha", "thi", "hoga", "hogi", "bhi", "sir", "bhai", "shuru", "padho",
            "padhkar", "dost", "madad", "uth", "utha", "jao", "bolu", "bolo", "likho", "run",
            "ko", "ka", "ki", "ke", "se", "par", "mein", "karein", "de", "do"
        }
        import re
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        matched_hinglish = tokens.intersection(hinglish_words)

        if len(matched_hinglish) >= 1:
            return "hinglish"

        return "en"

    def _transcribe_with_whisper(self, wav_bytes: bytes) -> Tuple[str, str]:
        """Optional Faster-Whisper transcription wrapper."""
        try:
            from faster_whisper import WhisperModel
            with self._lock:
                if self._whisper_model is None:
                    self._whisper_model = WhisperModel(
                        self.config.whisper_model_size,
                        device=self.config.whisper_device,
                        compute_type="int8"
                    )
            segments, info = self._whisper_model.transcribe(
                io.BytesIO(wav_bytes),
                beam_size=5,
                language="hi" if self.config.stt_engine == "hindi" else None
            )
            text = " ".join([seg.text.strip() for seg in segments])
            return text, info.language
        except Exception as e:
            logger.warning(f"Whisper inference error: {e}")
            return "", "en"

    def _transcribe_with_vosk(self, wav_bytes: bytes) -> Tuple[str, str]:
        """Optional Vosk offline transcription wrapper."""
        try:
            import json
            from vosk import KaldiRecognizer
            if self._vosk_model is None:
                return "", "en"
            rec = KaldiRecognizer(self._vosk_model, 16000)
            rec.AcceptWaveform(wav_bytes)
            res = json.loads(rec.FinalResult())
            text = res.get("text", "")
            return text, self._detect_language_heuristic(text)
        except Exception as e:
            logger.warning(f"Vosk error: {e}")
            return "", "en"
