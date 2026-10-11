"""
IRIS Audio Manager
Coordinates background microphone streaming, Voice Activity Detection (VAD),
wake-word triggering, speech recognition, audio feedback loop prevention, and mute controls.

Performance-optimized: dynamic pause thresholds (0.5s for wake word), fast single-pass
wake transcription, persistent mic session, and instant cached TTS acknowledgments.
"""

import time
import threading
from typing import Optional, Callable
from pathlib import Path

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.events import EventBus, EventType, Event
from ..core.state import StateManager, AssistantState
from .wake_word import WakeWordDetector
from .stt import SpeechToTextEngine
from .tts import TextToSpeechEngine

logger = get_logger("audio_manager")

# Timeout (seconds) — if user doesn't speak after wake, go back to IDLE
_LISTENING_TIMEOUT = 12.0
# Short phrase limit during idle (wake-word detection): keeps latency low
_WAKE_PHRASE_LIMIT = 3.5
# Longer phrase limit when user is actively giving a command
_COMMAND_PHRASE_LIMIT = 8.0
# How many consecutive timeouts in LISTENING before returning to IDLE
_MAX_LISTEN_TIMEOUTS = 3


class AudioManager:
    """Manages full audio lifecycle: background mic listener, wake word, and command routing."""

    def __init__(self, tts: Optional[TextToSpeechEngine] = None):
        self.config = get_config()
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.wake_detector = WakeWordDetector()
        self.stt = SpeechToTextEngine()
        self.tts = tts or TextToSpeechEngine()

        self._running = False
        self._listener_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Feedback loop prevention: Track TTS state
        self._is_tts_active = False
        # Track consecutive listen timeouts for auto-return to IDLE
        self._listen_timeout_count = 0
        # Timestamp when we entered LISTENING state
        self._listening_since: float = 0.0
        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        self.event_bus.subscribe(EventType.TTS_START, self._on_tts_start)
        self.event_bus.subscribe(EventType.TTS_FINISHED, self._on_tts_finished)
        self.event_bus.subscribe(EventType.TTS_INTERRUPTED, self._on_tts_finished)

    def _on_tts_start(self, event: Event) -> None:
        self._is_tts_active = True

    def _on_tts_finished(self, event: Event) -> None:
        def _clear():
            time.sleep(0.3)
            self._is_tts_active = False
        threading.Thread(target=_clear, daemon=True).start()

    def start_listening(self) -> bool:
        """Starts background microphone processing thread."""
        with self._lock:
            if self._running:
                return True
            self._running = True

        self._listener_thread = threading.Thread(target=self._audio_capture_loop, daemon=True)
        self._listener_thread.start()
        logger.info("Background audio capture thread started.")
        return True

    def stop_listening(self) -> None:
        """Stops microphone capture."""
        with self._lock:
            self._running = False
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2.0)
        logger.info("Background audio capture thread stopped.")

    def _audio_capture_loop(self) -> None:
        """Continuous audio loop with PyAudio / SpeechRecognition.
        
        Uses 0.5s pause_threshold during IDLE for instant wake detection,
        and 0.8s during LISTENING for complete command capture.
        """
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = self.config.energy_threshold
            recognizer.dynamic_energy_threshold = self.config.dynamic_energy_threshold

            device_index = self.config.microphone_index if self.config.microphone_index >= 0 else None
            
            with sr.Microphone(device_index=device_index, sample_rate=self.config.sample_rate) as source:
                logger.info(f"Microphone opened (device_index={device_index}). Quick noise calibration...")
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                logger.info(f"Microphone calibration complete. Energy threshold: {recognizer.energy_threshold:.1f}")

                while self._running:
                    # Check privacy mute
                    if self.state_manager.is_muted:
                        time.sleep(0.15)
                        continue

                    # If TTS is actively speaking, ignore mic audio to avoid acoustic feedback
                    if self._is_tts_active or self.tts.is_speaking:
                        time.sleep(0.08)
                        continue

                    current_state = self.state_manager.current_state

                    # Adjust pause threshold & phrase limits based on state (ultra-responsive low latency)
                    if current_state == AssistantState.LISTENING:
                        recognizer.pause_threshold = 0.5
                        recognizer.non_speaking_duration = 0.3
                        phrase_limit = _COMMAND_PHRASE_LIMIT
                        listen_timeout = 2.0
                        is_wake_check = False
                    else:
                        # Ultra fast 0.35s pause threshold for instant wake word detection
                        recognizer.pause_threshold = 0.35
                        recognizer.non_speaking_duration = 0.2
                        phrase_limit = _WAKE_PHRASE_LIMIT
                        listen_timeout = 1.5
                        is_wake_check = True

                    # Check listening timeout — if in LISTENING too long, go back to IDLE
                    if current_state == AssistantState.LISTENING and self._listening_since > 0:
                        elapsed = time.time() - self._listening_since
                        if elapsed > _LISTENING_TIMEOUT:
                            logger.info(f"Listening timeout ({elapsed:.1f}s). Returning to IDLE.")
                            self.state_manager.transition_to(AssistantState.IDLE)
                            self._listen_timeout_count = 0
                            self._listening_since = 0.0
                            continue

                    try:
                        # Listen for utterance phrase
                        audio_data = recognizer.listen(
                            source,
                            timeout=listen_timeout,
                            phrase_time_limit=phrase_limit
                        )

                        # Process in worker thread to prevent blocking mic stream
                        threading.Thread(
                            target=self._process_utterance,
                            args=(audio_data, is_wake_check),
                            daemon=True
                        ).start()

                    except sr.WaitTimeoutError:
                        if current_state == AssistantState.LISTENING:
                            self._listen_timeout_count += 1
                            if self._listen_timeout_count >= _MAX_LISTEN_TIMEOUTS:
                                logger.info("Max listen timeouts reached. Returning to IDLE.")
                                self.state_manager.transition_to(AssistantState.IDLE)
                                self._listen_timeout_count = 0
                                self._listening_since = 0.0
                        continue
                    except Exception as e:
                        if self._running:
                            logger.debug(f"Audio listen tick: {e}")
                        time.sleep(0.1)

        except Exception as e:
            logger.error(f"Microphone capture loop failed: {e}", exc_info=True)
            self.event_bus.emit(EventType.ERROR_OCCURRED, {"error": str(e), "subsystem": "audio"})

    def _process_utterance(self, audio_data, is_wake_check: bool) -> None:
        """Processes captured audio phrase against wake word or active command."""
        if self._is_tts_active or self.tts.is_speaking or self.state_manager.is_muted:
            return

        current_state = self.state_manager.current_state
        t0 = time.time()

        try:
            # 1. Transcribe audio (fast mode for wake word check)
            transcription, detected_lang = self.stt.transcribe_audio_data(
                audio_data,
                is_wake_word_check=is_wake_check
            )
            t_transcribe = time.time() - t0
            
            if not transcription or len(transcription.strip()) == 0:
                return

            logger.info(f"Audio captured [State={current_state.value}] ({t_transcribe:.2f}s): '{transcription}'")

            # 2. Check wake word if currently IDLE
            if current_state == AssistantState.IDLE or is_wake_check:
                is_wake, matched_phrase, remaining_cmd = self.wake_detector.check_text(transcription)
                
                if is_wake:
                    logger.info(f"Wake word detected! Match='{matched_phrase}', Remainder='{remaining_cmd}' (total_latency: {time.time()-t0:.2f}s)")
                    self.event_bus.emit(EventType.WAKE_WORD_DETECTED, {
                        "phrase": matched_phrase,
                        "remaining": remaining_cmd
                    })
                    
                    self.state_manager.transition_to(AssistantState.LISTENING)
                    self._listening_since = time.time()
                    self._listen_timeout_count = 0

                    # If user spoke command in the same breath (e.g. "IRIS Chrome kholo")
                    if remaining_cmd and len(remaining_cmd.strip()) > 0:
                        self.handle_user_command(remaining_cmd.strip(), detected_lang)
                    else:
                        # Instant wake response using cached TTS (<10ms)
                        greeting = self.wake_detector.get_greeting_response(matched_phrase)
                        self.state_manager.transition_to(AssistantState.SPEAKING)
                        self.tts.speak(
                            greeting,
                            on_complete=lambda: self._enter_listening_state(),
                            block=False
                        )
                return

            # 3. If currently in LISTENING state, this utterance is the user's active command
            elif current_state == AssistantState.LISTENING:
                self._listen_timeout_count = 0
                self.handle_user_command(transcription, detected_lang)

            # 4. If THINKING/SPEAKING and user says wake word again, treat as new command
            elif current_state in (AssistantState.THINKING, AssistantState.SPEAKING):
                is_wake, matched_phrase, remaining_cmd = self.wake_detector.check_text(transcription)
                if is_wake and remaining_cmd and len(remaining_cmd.strip()) > 0:
                    logger.info(f"Interrupting current state with new command: '{remaining_cmd}'")
                    self.tts.stop()
                    self.state_manager.transition_to(AssistantState.IDLE)
                    time.sleep(0.1)
                    self.state_manager.transition_to(AssistantState.LISTENING)
                    self._listening_since = time.time()
                    self._listen_timeout_count = 0
                    self.handle_user_command(remaining_cmd.strip(), detected_lang)

        except Exception as e:
            logger.error(f"Error processing utterance: {e}", exc_info=True)

    def _enter_listening_state(self) -> None:
        """Transition to LISTENING with timestamp tracking."""
        self.state_manager.transition_to(AssistantState.LISTENING)
        self._listening_since = time.time()
        self._listen_timeout_count = 0

    def handle_user_command(self, command_text: str, detected_lang: str = "hinglish") -> None:
        """Dispatches recognized command to the EventBus."""
        logger.info(f"Handling user command: '{command_text}' ({detected_lang})")
        self.state_manager.transition_to(AssistantState.THINKING)
        self._listening_since = 0.0
        self.event_bus.emit(EventType.SPEECH_RECOGNIZED, {
            "text": command_text,
            "language": detected_lang
        })
