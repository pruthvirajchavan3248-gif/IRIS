"""
IRIS State Management Subsystem
Tracks assistant modes: Idle, Listening, Thinking, Speaking, Muted, Error.
"""

from enum import Enum
import threading
from typing import Optional
from .events import EventBus, EventType


class AssistantState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    MUTED = "muted"
    ERROR = "error"


class StateManager:
    """Singleton state manager with thread-safe transitions and event notifications."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StateManager, cls).__new__(cls)
                cls._instance._current_state = AssistantState.IDLE
                cls._instance._previous_state = AssistantState.IDLE
                cls._instance._event_bus = EventBus()
                cls._instance._state_lock = threading.RLock()
                cls._instance._is_orb_visible = True
            return cls._instance

    @property
    def current_state(self) -> AssistantState:
        with self._state_lock:
            return self._current_state

    @property
    def previous_state(self) -> AssistantState:
        with self._state_lock:
            return self._previous_state

    @property
    def is_muted(self) -> bool:
        with self._state_lock:
            return self._current_state == AssistantState.MUTED

    @property
    def is_orb_visible(self) -> bool:
        with self._state_lock:
            return self._is_orb_visible

    def set_orb_visible(self, visible: bool) -> None:
        with self._state_lock:
            self._is_orb_visible = visible
        self._event_bus.emit(EventType.ORB_VISIBILITY_TOGGLED, {"visible": visible})

    def transition_to(self, new_state: AssistantState, metadata: Optional[dict] = None) -> bool:
        with self._state_lock:
            if self._current_state == new_state:
                return False
            
            # If muted, only allow transitions to IDLE or un-mute unless forced
            if self._current_state == AssistantState.MUTED and new_state not in [AssistantState.IDLE, AssistantState.MUTED]:
                return False

            self._previous_state = self._current_state
            self._current_state = new_state
            old_state = self._previous_state

        payload = {
            "old_state": old_state.value,
            "new_state": new_state.value,
            "metadata": metadata or {}
        }
        self._event_bus.emit(EventType.STATE_CHANGED, payload)
        return True

    def toggle_mute(self) -> bool:
        """Toggles between MUTED and IDLE."""
        with self._state_lock:
            if self._current_state == AssistantState.MUTED:
                self.transition_to(AssistantState.IDLE)
                return False
            else:
                self.transition_to(AssistantState.MUTED)
                return True
