"""
IRIS Text-To-Speech (TTS) Engine
Generates high quality natural female speech via Microsoft Edge TTS with offline pyttsx3 fallback.
Includes persistent audio disk cache for INSTANT wake responses and frequent acknowledgments.
Supports interruption handling, asynchronous playback, and language-aware neural voice selection.
"""

import os
import asyncio
import hashlib
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Callable
import pygame

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.events import EventBus, EventType

logger = get_logger("tts")


class TextToSpeechEngine:
    """Natural female speech synthesis with Edge-TTS, persistent cache, and offline SAPI5 fallback."""

    def __init__(self):
        self.config = get_config()
        self.event_bus = EventBus()
        self._is_speaking = False
        self._stop_requested = False
        self._lock = threading.Lock()
        self._pyttsx3_engine = None

        # Persistent audio cache directory
        self.cache_dir = self.config.temp_audio_dir / "tts_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Persistent event loop for edge-tts (avoids creating new loop per call)
        self._async_loop = None
        self._async_thread = None
        self._init_audio_player()
        self._init_pyttsx3()
        self._init_async_loop()

        # Pre-warm common responses in background thread
        threading.Thread(target=self._prewarm_cache, daemon=True).start()

    def _init_audio_player(self) -> None:
        """Initializes PyGame mixer for high quality audio playback."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=1024)
            logger.info("Pygame mixer initialized for TTS playback.")
        except Exception as e:
            logger.warning(f"Pygame mixer init warning: {e}")

    def _init_pyttsx3(self) -> None:
        """Configures Windows SAPI5 offline female voice fallback."""
        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            voices = self._pyttsx3_engine.getProperty("voices")
            female_voice = None
            for v in voices:
                if any(kw in v.name.lower() for kw in ["zira", "female", "eva", "swara", "neerja"]):
                    female_voice = v.id
                    break
            if female_voice:
                self._pyttsx3_engine.setProperty("voice", female_voice)
            self._pyttsx3_engine.setProperty("rate", 175)
            logger.info("Offline pyttsx3 SAPI5 fallback engine initialized.")
        except Exception as e:
            logger.warning(f"pyttsx3 fallback not available: {e}")

    def _init_async_loop(self) -> None:
        """Creates a persistent background event loop for async edge-tts calls."""
        self._async_loop = asyncio.new_event_loop()
        self._async_thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True
        )
        self._async_thread.start()

    def _run_event_loop(self) -> None:
        """Runs the persistent event loop in a background thread."""
        asyncio.set_event_loop(self._async_loop)
        self._async_loop.run_forever()

    def _get_cache_path(self, text: str, voice: str) -> Path:
        """Computes deterministic cache filepath based on text hash and voice."""
        key = f"{voice}:{text.strip().lower()}"
        text_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"tts_{text_hash}.mp3"

    def _prewarm_cache(self) -> None:
        """Pre-generates common responses in background so they play instantly (<5ms)."""
        user_name = self.config.user_name
        common_phrases = [
            f"Ji {user_name}, IRIS ready hai. Main aapki kya madad kar sakti hoon?",
            f"Ji {user_name}, IRIS ready hai. Bataiye kya karna hai?",
            f"Ji {user_name}, bataiye?",
            f"Ji {user_name}, sun rahi hoon.",
            f"Google Chrome open kar rahi hoon, {user_name}.",
            f"WhatsApp open kar rahi hoon, {user_name}.",
            f"Notepad open kar rahi hoon, {user_name}.",
            f"VS Code editor open kar rahi hoon, {user_name}.",
            f"Calculator open kar rahi hoon, {user_name}.",
            f"Paint open kar rahi hoon, {user_name}.",
            f"File Explorer open kar rahi hoon, {user_name}.",
            f"Terminal open kar rahi hoon, {user_name}.",
            f"Settings open kar rahi hoon, {user_name}.",
            f"Task Manager open kar rahi hoon, {user_name}.",
            f"Volume badha diya hai, {user_name}.",
            f"Volume kam kar diya hai, {user_name}.",
            f"Volume mute kar diya hai, {user_name}.",
            f"Screenshot le liya hai, {user_name}.",
            f"Workstation lock kar diya hai, {user_name}.",
            f"Main bilkul theek hoon, {user_name}! Aapki seva mein hamesha taiyaar. Bataiye kya kar sakti hoon aapke liye?",
            f"Aapka shukriya, {user_name}! Kisi bhi waqt bula lijiyega.",
            f"YouTube open kar diya hai, {user_name}.",
            f"Alvida {user_name}! Aapka din shubh rahe.",
            f"Microphone mute kar rahi hoon, {user_name}.",
            f"Ji {user_name}, main background mein chali jaati hoon.",
            f"Ji {user_name}, main samne aa gayi hoon.",
            f"Current tab close kar diya hai, {user_name}.",
            f"Naya browser tab open kar diya hai, {user_name}.",
            f"Dictation mode activate kar diya hai. Cursor wali jagah par main type karungi.",
        ]
        time.sleep(0.5)  # Quick wait for app startup
        for phrase in common_phrases:
            voice = self.select_voice_for_text(phrase)
            cache_file = self._get_cache_path(phrase, voice)
            if not cache_file.exists() or cache_file.stat().st_size == 0:
                try:
                    self._synthesize_to_file(phrase, voice, cache_file)
                    logger.debug(f"Pre-cached TTS phrase: '{phrase[:30]}...'")
                except Exception as e:
                    logger.debug(f"Pre-warm failed for phrase '{phrase[:20]}': {e}")
                    break  # If network down, stop prewarming

    def _synthesize_to_file(self, text: str, voice: str, dest_path: Path) -> bool:
        """Synthesizes text using edge_tts and saves directly to destination path."""
        import edge_tts
        temp_dest = dest_path.with_suffix(".tmp")
        try:
            async def _generate():
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=self.config.tts_rate,
                    pitch=self.config.tts_pitch
                )
                await communicate.save(str(temp_dest))

            future = asyncio.run_coroutine_threadsafe(_generate(), self._async_loop)
            future.result(timeout=3.5)

            if temp_dest.exists() and temp_dest.stat().st_size > 0:
                temp_dest.replace(dest_path)
                return True
            return False
        except Exception as e:
            if temp_dest.exists():
                try:
                    temp_dest.unlink()
                except Exception:
                    pass
            logger.warning(f"Synthesis to file failed: {e}")
            return False

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._is_speaking

    def select_voice_for_text(self, text: str) -> str:
        """Selects appropriate Edge-TTS female voice model based on text script/language."""
        devanagari_count = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
        if devanagari_count > 0:
            return self.config.edge_voice_hi  # hi-IN-SwaraNeural

        hinglish_markers = {"ji", "sir", "hai", "karo", "kholo", "samjhao", "main", "aap", "dost", "kaise", "kya", "bataiye", "rahi"}
        words = set(text.lower().split())
        if words.intersection(hinglish_markers):
            return self.config.edge_voice_hi  # Swara handles Hinglish romanized script gracefully

        return self.config.edge_voice_en  # en-IN-NeerjaNeural

    def speak(self, text: str, on_complete: Optional[Callable[[], None]] = None, block: bool = True) -> None:
        """Synthesizes and speaks text synchronously or asynchronously."""
        if not text or not text.strip():
            if on_complete:
                on_complete()
            return

        clean_text = text.strip()

        if block:
            self._speak_internal(clean_text)
            if on_complete:
                on_complete()
        else:
            t = threading.Thread(target=self._run_async_wrapper, args=(clean_text, on_complete), daemon=True)
            t.start()

    def _run_async_wrapper(self, text: str, on_complete: Optional[Callable[[], None]]) -> None:
        self._speak_internal(text)
        if on_complete:
            on_complete()

    def stop(self) -> None:
        """Interrupts current speech playback immediately."""
        with self._lock:
            self._stop_requested = True

        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

        if self._pyttsx3_engine:
            try:
                self._pyttsx3_engine.stop()
            except Exception:
                pass

        logger.info("TTS playback interrupted.")
        self.event_bus.emit(EventType.TTS_INTERRUPTED, {})

    def _speak_internal(self, text: str) -> None:
        with self._lock:
            self._is_speaking = True
            self._stop_requested = False

        self.event_bus.emit(EventType.TTS_START, {"text": text})
        logger.info(f"Speaking: '{text}'")

        success = False
        # 1. Primary: Edge-TTS (checks disk cache first for 3ms instant response)
        if self.config.tts_engine == "edge_tts":
            success = self._speak_edge_tts(text)

        # 2. Fallback: pyttsx3 offline Windows voice
        if not success and not self._stop_requested:
            logger.warning("Edge-TTS unavailable or failed. Using pyttsx3 fallback.")
            self._speak_pyttsx3(text)

        with self._lock:
            self._is_speaking = False

        self.event_bus.emit(EventType.TTS_FINISHED, {"text": text})

    def _speak_edge_tts(self, text: str) -> bool:
        """Plays audio from disk cache if present, else synthesizes via Edge-TTS and caches it."""
        voice = self.select_voice_for_text(text)
        cache_file = self._get_cache_path(text, voice)

        # Check if already cached on disk
        if cache_file.exists() and cache_file.stat().st_size > 0:
            logger.info(f"Playing TTS from instant local cache: {cache_file.name}")
            return self._play_audio_file(cache_file)

        # Synthesize and cache
        logger.info(f"Synthesizing new speech via Edge-TTS ({voice})...")
        synthesized = self._synthesize_to_file(text, voice, cache_file)
        if synthesized and cache_file.exists():
            return self._play_audio_file(cache_file)

        return False

    def _play_audio_file(self, file_path: Path) -> bool:
        """Loads and plays an audio file using Pygame mixer."""
        if self._stop_requested:
            return False

        try:
            if not pygame.mixer.get_init():
                self._init_audio_player()

            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                if self._stop_requested:
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.04)

            return True
        except Exception as e:
            logger.error(f"Error during audio playback: {e}")
            return False
        finally:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

    def _speak_pyttsx3(self, text: str) -> bool:
        """Speaks text using local Windows SAPI5 voice."""
        if not self._pyttsx3_engine:
            return False
        try:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"pyttsx3 playback error: {e}")
            return False
