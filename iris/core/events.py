"""
IRIS Event Bus Subsystem
Provides decoupled, thread-safe publish/subscribe event routing across UI and audio loops.
"""

from enum import Enum
import threading
from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
import time


class EventType(str, Enum):
    # State changes
    STATE_CHANGED = "state_changed"
    
    # Audio & Voice Pipeline
    WAKE_WORD_DETECTED = "wake_word_detected"
    SPEECH_START = "speech_start"
    SPEECH_INTERIM = "speech_interim"
    SPEECH_RECOGNIZED = "speech_recognized"
    TTS_START = "tts_start"
    TTS_FINISHED = "tts_finished"
    TTS_INTERRUPTED = "tts_interrupted"
    
    # AI & Intent
    INTENT_PROCESSING = "intent_processing"
    INTENT_RESOLVED = "intent_resolved"
    AI_RESPONSE_GENERATED = "ai_response_generated"
    
    # System & Automation
    COMMAND_EXECUTION_REQUEST = "command_execution_request"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_FAILED = "command_failed"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_RECEIVED = "confirmation_received"
    
    # Controls
    MIC_MUTE_TOGGLED = "mic_mute_toggled"
    ORB_VISIBILITY_TOGGLED = "orb_visibility_toggled"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SETTINGS_REQUESTED = "settings_requested"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "core"


class EventBus:
    """Thread-safe event dispatcher for IRIS components."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
                cls._instance._sub_lock = threading.RLock()
            return cls._instance

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        with self._sub_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        with self._sub_lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:
        with self._sub_lock:
            handlers = list(self._subscribers.get(event.type, []))
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Catch handler failures gracefully to avoid stopping the event bus
                print(f"Error in EventBus handler for {event.type}: {e}")

    def emit(self, event_type: EventType, data: Dict[str, Any] = None, source: str = "core") -> None:
        self.publish(Event(type=event_type, data=data or {}, source=source))
