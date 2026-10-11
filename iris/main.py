"""
IRIS Main Application Entry Point
Initializes Qt application, floating orb, system tray, audio listener, and execution dispatcher.
"""

import sys
import os
import signal
import time
import threading
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication

from .core.config import get_config
from .core.logger import setup_logger, get_logger
from .core.events import EventBus, EventType, Event
from .core.state import AssistantState, StateManager
from .database.db import get_db
from .speech.tts import TextToSpeechEngine
from .speech.audio_manager import AudioManager
from .ai.intent_engine import IntentEngine, ResolvedIntent
from .automation.windows_controller import WindowsController
from .automation.dictation import DictationManager
from .automation.browser_controller import BrowserController
from .automation.project_runner import ProjectRunner
from .automation.security import SecurityGuard
from .ui.orb_window import FloatingOrbWindow
from .ui.tray_icon import IrisTrayIcon
from .ui.settings_dialog import SettingsAndDatabaseViewer

logger = get_logger("main")


class MainDispatcher(QObject):
    """Bridge between background audio threads and Qt main GUI thread."""
    speech_recognized_signal = Signal(str, str)
    settings_requested_signal = Signal()
    shutdown_signal = Signal()
    speak_and_idle_signal = Signal(str)

    def __init__(self, assistant_app):
        super().__init__()
        self.app = assistant_app
        self.speech_recognized_signal.connect(self.app.process_speech_command)
        self.settings_requested_signal.connect(self.app.show_settings_dialog)
        self.shutdown_signal.connect(self.app.shutdown)
        self.speak_and_idle_signal.connect(self.app._speak_and_idle_qt)


class IrisAssistantApp:
    """Master controller for IRIS Virtual Assistant."""

    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger("iris", level=self.config.log_level)
        self.logger.info("==========================================")
        self.logger.info("   Starting IRIS Virtual Assistant v1.0   ")
        self.logger.info("==========================================")

        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.db = get_db()

        # Automation & Executors
        self.windows_controller = WindowsController()
        self.dictation_manager = DictationManager()
        self.browser_controller = BrowserController()
        self.project_runner = ProjectRunner()
        self.security_guard = SecurityGuard()

        # Speech & AI
        self.tts = TextToSpeechEngine()
        self.intent_engine = IntentEngine()
        self.audio_manager = AudioManager(tts=self.tts)

        # Qt GUI
        self.dispatcher = MainDispatcher(self)
        self.orb_window = FloatingOrbWindow(on_orb_clicked=self.on_orb_manual_tap)
        self.tray_icon = IrisTrayIcon()
        self.settings_dialog: Optional[SettingsAndDatabaseViewer] = None

        # State recovery timer — prevents getting stuck in THINKING/SPEAKING forever
        self._state_recovery_timer = QTimer()
        self._state_recovery_timer.setInterval(30000)  # 30 second safety net
        self._state_recovery_timer.timeout.connect(self._recover_stuck_state)
        self._state_recovery_timer.start()

        self._subscribe_events()

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(EventType.SPEECH_RECOGNIZED, self._on_speech_recognized_event)
        self.event_bus.subscribe(EventType.SETTINGS_REQUESTED, lambda e: self.dispatcher.settings_requested_signal.emit())
        self.event_bus.subscribe(EventType.SYSTEM_SHUTDOWN, lambda e: self.dispatcher.shutdown_signal.emit())

    def _on_speech_recognized_event(self, event: Event) -> None:
        text = event.data.get("text", "")
        lang = event.data.get("language", "hinglish")
        self.dispatcher.speech_recognized_signal.emit(text, lang)

    def _recover_stuck_state(self) -> None:
        """Safety net: if state has been THINKING or SPEAKING for too long, reset to IDLE."""
        current = self.state_manager.current_state
        if current in (AssistantState.THINKING, AssistantState.SPEAKING):
            self.logger.warning(f"State recovery: stuck in {current.value}, resetting to IDLE")
            self.state_manager.transition_to(AssistantState.IDLE)

    def on_orb_manual_tap(self) -> None:
        """Called when user clicks the floating orb directly."""
        if self.state_manager.is_muted:
            self.state_manager.toggle_mute()
            return

        if self.state_manager.current_state == AssistantState.IDLE:
            self.logger.info("Orb manually tapped. Listening for user...")
            self.state_manager.transition_to(AssistantState.LISTENING)
            greeting = f"Ji {self.config.user_name}, bataiye?"
            self.tts.speak(greeting, on_complete=lambda: None, block=False)
        elif self.state_manager.current_state in [AssistantState.SPEAKING, AssistantState.THINKING]:
            self.tts.stop()
            self.state_manager.transition_to(AssistantState.IDLE)

    @Slot(str, str)
    def process_speech_command(self, utterance: str, language: str) -> None:
        """Dispatches speech processing to a background thread to avoid blocking Qt UI."""
        # Handle dictation mode immediately (lightweight, no Gemini call)
        if self.dictation_manager.is_active:
            lower = utterance.lower()
            if any(kw in lower for kw in ["stop typing", "dictation band karo", "ruk jao", "type band karo"]):
                self.dictation_manager.stop_dictation()
                resp = f"Dictation mode band kar diya hai, {self.config.user_name}."
                self._speak_and_idle(resp)
                return
            else:
                self.dictation_manager.type_text(utterance)
                # Keep listening in dictation mode
                self.state_manager.transition_to(AssistantState.LISTENING)
                return

        # Heavy processing (intent resolution + Gemini) goes to background thread
        t = threading.Thread(
            target=self._process_command_background,
            args=(utterance, language),
            daemon=True
        )
        t.start()

    def _process_command_background(self, utterance: str, language: str) -> None:
        """Runs intent resolution and action dispatch in background thread."""
        start_time = time.time()
        self.logger.info(f"Processing command: '{utterance}' [{language}]")

        try:
            # 1. Resolve Intent (may call Gemini — can take seconds)
            resolved: ResolvedIntent = self.intent_engine.resolve(utterance, language)
            action_type = resolved.action_type
            params = resolved.parameters
            speech_resp = resolved.speech_response

            # 2. Security validation
            is_allowed, req_conf, sec_msg = self.security_guard.validate_action(action_type, params)
            if not is_allowed:
                self.logger.warning(f"Security block: {sec_msg}")
                self.db.log_command(utterance, resolved.intent, params, "SECURITY_BLOCKED", 0, sec_msg)
                self.dispatcher.speak_and_idle_signal.emit(
                    f"Yeh action execute nahi kiya ja sakta, {self.config.user_name}. {sec_msg}"
                )
                return

            # 3. Dispatch Action
            exec_status = "SUCCESS"
            error_msg = ""

            try:
                if action_type == "launch_app":
                    app_name = params.get("app_name", "")
                    success, msg = self.windows_controller.launch_application(app_name)
                    if not success:
                        exec_status = "FAILED"
                        error_msg = msg
                        speech_resp = f"Maaf kijiyega, {app_name} start nahi ho paaya."

                elif action_type == "close_app":
                    app_name = params.get("app_name", "")
                    success, msg = self.windows_controller.close_application(app_name)
                    if not success:
                        exec_status = "FAILED"
                        error_msg = msg
                        speech_resp = f"Maaf kijiyega, {app_name} close nahi ho paaya ya running nahi mila."

                elif action_type == "launch_and_type":
                    app_name = params.get("app_name", "")
                    text_to_type = params.get("text_to_type", "")
                    self.windows_controller.launch_application(app_name)
                    time.sleep(1.2)  # Allow target app window to mount and focus
                    self.dictation_manager.type_text(text_to_type)

                elif action_type == "type_text":
                    text_to_type = params.get("text", "")
                    self.dictation_manager.type_text(text_to_type)

                elif action_type == "close_tab":
                    self.browser_controller.close_tab(self.windows_controller)

                elif action_type == "new_tab":
                    self.browser_controller.new_tab(self.windows_controller)

                elif action_type == "next_tab":
                    self.browser_controller.next_tab(self.windows_controller)

                elif action_type == "prev_tab":
                    self.browser_controller.previous_tab(self.windows_controller)

                elif action_type == "reload_page":
                    self.browser_controller.reload_page(self.windows_controller)

                elif action_type == "open_url":
                    url = params.get("url", "")
                    self.browser_controller.open_url(url)

                elif action_type == "web_search":
                    query = params.get("query", "")
                    engine = params.get("engine", "google")
                    self.browser_controller.search_web(query, engine)

                elif action_type == "start_dictation":
                    self.dictation_manager.start_dictation()

                elif action_type == "run_registered_project":
                    proj_name = params.get("project_name", "")
                    success, msg, proj = self.project_runner.run_project(proj_name)
                    if not success:
                        exec_status = "FAILED"
                        error_msg = msg
                        speech_resp = f"{msg}"

                elif action_type == "open_registered_project":
                    is_recent = params.get("recent", False)
                    success, msg, proj = self.project_runner.open_project_in_editor(recent=is_recent)
                    if not success:
                        exec_status = "FAILED"
                        error_msg = msg
                        speech_resp = f"{msg}"

                elif action_type in ("read_webpage", "summarize_webpage"):
                    active_title = self.windows_controller.get_active_window_title()
                    extracted_text = self.windows_controller.read_visible_page_text()
                    if extracted_text and len(extracted_text.strip()) > 10:
                        speech_resp = f"Screen text: {extracted_text[:300]}"
                    else:
                        speech_resp = f"Active window '{active_title}' par koi readable text nahi mila, {self.config.user_name}."

                elif action_type == "translate":
                    clipboard_txt = self.windows_controller.get_clipboard_text()
                    if clipboard_txt:
                        speech_resp = f"Clipboard text: '{clipboard_txt[:60]}'. Translation ready hai."
                    else:
                        speech_resp = f"Pehle text copy kijiye, phir main translate kar dungi, {self.config.user_name}."

                elif action_type == "control_volume":
                    direction = params.get("action", "up")
                    self.windows_controller.control_volume(direction)

                elif action_type == "take_screenshot":
                    ok, path = self.windows_controller.take_screenshot()
                    if not ok:
                        speech_resp = f"Screenshot lene mein dikkat aayi, {self.config.user_name}."

                elif action_type == "lock_workstation":
                    self.windows_controller.lock_workstation()

                elif action_type == "hide_orb":
                    self.state_manager.set_orb_visible(False)

                elif action_type == "show_orb":
                    self.state_manager.set_orb_visible(True)

                elif action_type == "mute_mic":
                    self.state_manager.transition_to(AssistantState.MUTED)

                elif action_type == "exit_app":
                    self.dispatcher.speak_and_idle_signal.emit(speech_resp)
                    time.sleep(2)
                    self.dispatcher.shutdown_signal.emit()
                    return

            except Exception as e:
                exec_status = "FAILED"
                error_msg = str(e)
                self.logger.error(f"Execution error for action {action_type}: {e}")
                speech_resp = f"Action execute karne mein samasya aayi: {str(e)}"

            # 4. Log command metrics to DB
            duration_ms = int((time.time() - start_time) * 1000)
            self.db.log_command(utterance, resolved.intent, params, exec_status, duration_ms, error_msg)

            # 5. Speak response (emit signal to Qt thread)
            self.dispatcher.speak_and_idle_signal.emit(speech_resp)

        except Exception as e:
            self.logger.error(f"Background command processing error: {e}", exc_info=True)
            self.dispatcher.speak_and_idle_signal.emit(
                f"Maaf kijiye {self.config.user_name}, processing mein error aayi."
            )

    @Slot(str)
    def _speak_and_idle_qt(self, speech_text: str) -> None:
        """Qt-thread-safe wrapper for speak and idle."""
        self._speak_and_idle(speech_text)

    def _speak_and_idle(self, speech_text: str, on_done: Optional[callable] = None) -> None:
        """Speaks output and transitions state back to IDLE upon finish."""
        self.state_manager.transition_to(AssistantState.SPEAKING)
        
        def _finish():
            if on_done:
                on_done()
            else:
                self.state_manager.transition_to(AssistantState.IDLE)

        self.tts.speak(speech_text, on_complete=_finish, block=False)

    @Slot()
    def show_settings_dialog(self) -> None:
        """Opens settings and database viewer dialog."""
        if not self.settings_dialog:
            self.settings_dialog = SettingsAndDatabaseViewer()
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def start(self) -> None:
        """Launches audio thread and displays floating orb."""
        self.orb_window.show()
        self.audio_manager.start_listening()
        self.logger.info("IRIS Virtual Assistant initialized and active.")

    @Slot()
    def shutdown(self) -> None:
        """Gracefully terminates audio threads, closes windows, and exits."""
        self.logger.info("Shutting down IRIS Virtual Assistant...")
        self.audio_manager.stop_listening()
        self.tts.stop()
        if self.orb_window:
            self.orb_window.close()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()


def main():
    """Main launcher."""
    # Ensure high DPI scaling on modern Windows displays
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("IRIS Virtual Assistant")
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray when orb is hidden!

    iris_app = IrisAssistantApp()
    iris_app.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
