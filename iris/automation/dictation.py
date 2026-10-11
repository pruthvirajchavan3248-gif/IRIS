"""
IRIS Dictation & Keystroke Injection
Fulfills voice command "Jo main bolu woh type karo" and direct typing actions.
Injects transcribed speech directly into whatever active window or text box has cursor focus.
"""

import time
import ctypes
from typing import Optional
from ..core.logger import get_logger
from ..core.events import EventBus, EventType

logger = get_logger("dictation")

# Windows SendInput constants for Unicode text injection
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    ]


class DictationManager:
    """Handles automated typing into active Windows input fields."""

    def __init__(self):
        self.is_active = False
        self.event_bus = EventBus()

    def start_dictation(self) -> None:
        """Enables dictation mode."""
        self.is_active = True
        logger.info("Dictation mode activated.")

    def stop_dictation(self) -> None:
        """Disables dictation mode."""
        self.is_active = False
        logger.info("Dictation mode deactivated.")

    def type_text(self, text: str, add_trailing_space: bool = True) -> bool:
        """Types unicode string into the currently focused window."""
        if not text:
            return False

        logger.info(f"Injecting keystrokes: '{text}'")
        try:
            # 1. Win32 SendInput (Handles Unicode, Hindi, English, symbols without clipboard pollution)
            for char in text:
                self._send_unicode_char(char)
                time.sleep(0.008)

            if add_trailing_space:
                self._send_unicode_char(" ")
            return True
        except Exception as e:
            logger.warning(f"Win32 SendInput failed, using clipboard paste fallback: {e}")
            try:
                # 2. Clipboard paste fallback (Ctrl+V)
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text + (" " if add_trailing_space else ""), win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()

                user32 = ctypes.windll.user32
                VK_CONTROL = 0x11
                VK_V = 0x56
                user32.keybd_event(VK_CONTROL, 0, 0, 0)
                user32.keybd_event(VK_V, 0, 0, 0)
                time.sleep(0.02)
                user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
                return True
            except Exception as e2:
                logger.error(f"Dictation fallback failed: {e2}")
                return False

    @staticmethod
    def _send_unicode_char(char: str) -> None:
        """Sends a single Unicode character using Win32 SendInput."""
        code = ord(char)
        
        # Key Down
        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.union.ki.wVk = 0
        inp_down.union.ki.wScan = code
        inp_down.union.ki.dwFlags = KEYEVENTF_UNICODE
        inp_down.union.ki.time = 0
        inp_down.union.ki.dwExtraInfo = None

        # Key Up
        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.union.ki.wVk = 0
        inp_up.union.ki.wScan = code
        inp_up.union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        inp_up.union.ki.time = 0
        inp_up.union.ki.dwExtraInfo = None

        inputs = (INPUT * 2)(inp_down, inp_up)
        ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
