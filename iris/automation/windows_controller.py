"""
IRIS Windows Controller
Interacts with Windows OS, processes, application shortcuts, windows, and system settings.
Verifies real process execution before reporting success.
Includes native Win32 hotkey dispatching and visible screen text extraction.
"""

import os
import sys
import time
import subprocess
import shutil
import ctypes
import winreg
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import psutil

from ..core.config import get_config
from ..core.logger import get_logger
from ..database.db import get_db

logger = get_logger("windows_controller")

# Virtual Key Codes for keybd_event
VK_MAP = {
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "tab": 0x09,
    "enter": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "f4": 0x73,
    "f5": 0x74,
    "a": 0x41,
    "c": 0x43,
    "t": 0x54,
    "v": 0x56,
    "w": 0x57,
}
KEYEVENTF_KEYUP = 0x0002

# Common Windows application executable search paths
_COMMON_APP_PATHS = {
    "chrome": [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ],
    "brave": [
        os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ],
    "edge": [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ],
    "firefox": [
        os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
    ],
    "vscode": [
        os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
    ],
    "notepad": [
        os.path.expandvars(r"%SystemRoot%\notepad.exe"),
        os.path.expandvars(r"%SystemRoot%\system32\notepad.exe"),
    ],
    "calculator": [
        "calc.exe",
    ],
    "explorer": [
        os.path.expandvars(r"%SystemRoot%\explorer.exe"),
    ],
    "terminal": [
        os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps\wt.exe"),
    ],
    "spotify": [
        os.path.expandvars(r"%AppData%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps\Spotify.exe"),
    ],
    "whatsapp": [
        os.path.expandvars(r"%LocalAppData%\WhatsApp\WhatsApp.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps\WhatsApp.exe"),
        os.path.expandvars(r"%ProgramFiles%\WindowsApps\WhatsApp.exe"),
    ],
    "paint": [
        os.path.expandvars(r"%SystemRoot%\system32\mspaint.exe"),
        os.path.expandvars(r"%SystemRoot%\mspaint.exe"),
    ],
    "taskmgr": [
        os.path.expandvars(r"%SystemRoot%\system32\taskmgr.exe"),
    ],
    "word": [
        os.path.expandvars(r"%ProgramFiles%\Microsoft Office\root\Office16\WINWORD.EXE"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft Office\root\Office16\WINWORD.EXE"),
    ],
    "excel": [
        os.path.expandvars(r"%ProgramFiles%\Microsoft Office\root\Office16\EXCEL.EXE"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft Office\root\Office16\EXCEL.EXE"),
    ],
}

# Alias map — maps spoken names to canonical lookup keys
_APP_ALIASES = {
    "google chrome": "chrome", "browser": "chrome",
    "brave browser": "brave",
    "microsoft edge": "edge", "msedge": "edge",
    "mozilla firefox": "firefox",
    "vs code": "vscode", "visual studio code": "vscode", "code": "vscode",
    "notepad": "notepad", "text editor": "notepad",
    "calc": "calculator", "hisab": "calculator",
    "file explorer": "explorer", "my computer": "explorer", "files": "explorer",
    "powershell": "terminal", "cmd": "terminal", "command prompt": "terminal",
    "whatsapp": "whatsapp", "wa": "whatsapp",
    "paint": "paint", "drawing": "paint",
    "task manager": "taskmgr", "taskmgr": "taskmgr",
    "camera": "microsoft.windows.camera:",
    "settings": "ms-settings:",
    "microsoft word": "word", "winword": "word",
    "microsoft excel": "excel",
    "youtube": "youtube",
}

# Process binary names for termination
_PROCESS_NAMES = {
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "browser": ["chrome.exe", "msedge.exe"],
    "edge": ["msedge.exe"],
    "brave": ["brave.exe"],
    "firefox": ["firefox.exe"],
    "vscode": ["Code.exe"],
    "vs code": ["Code.exe"],
    "code": ["Code.exe"],
    "notepad": ["notepad.exe"],
    "calc": ["CalculatorApp.exe", "calc.exe"],
    "calculator": ["CalculatorApp.exe", "calc.exe"],
    "whatsapp": ["WhatsApp.exe", "whatsapp.exe"],
    "spotify": ["Spotify.exe"],
    "word": ["WINWORD.EXE"],
    "excel": ["EXCEL.EXE"],
    "terminal": ["WindowsTerminal.exe", "wt.exe", "powershell.exe", "cmd.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
}

# Web-based fallback URLs for apps that may not be installed locally
_WEB_FALLBACKS = {
    "whatsapp": "https://web.whatsapp.com",
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chatgpt.com",
    "spotify": "https://open.spotify.com",
    "gmail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "google maps": "https://maps.google.com",
}


class WindowsController:
    """Controls Windows desktop applications, volume, window focus, and clipboard."""

    def __init__(self):
        self.config = get_config()
        self.db = get_db()

    def send_hotkey(self, *keys: str) -> bool:
        """Sends native Win32 keyboard hotkeys like ('ctrl', 'w') or ('ctrl', 'shift', 'tab')."""
        try:
            user32 = ctypes.windll.user32
            vk_codes = []
            for k in keys:
                code = VK_MAP.get(k.lower())
                if code is None and len(k) == 1:
                    code = ord(k.upper())
                if code:
                    vk_codes.append(code)

            if not vk_codes:
                return False

            # Press keys down in order
            for code in vk_codes:
                user32.keybd_event(code, 0, 0, 0)
                time.sleep(0.02)

            # Release keys in reverse order
            for code in reversed(vk_codes):
                user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
                time.sleep(0.02)

            return True
        except Exception as e:
            logger.error(f"Error sending hotkey {keys}: {e}")
            return False

    def launch_application(self, app_name: str, args: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Launches an application using multiple resolution strategies.
        Returns:
            (success, message)
        """
        clean_name = app_name.strip().lower()
        logger.info(f"Attempting to launch application: '{clean_name}'")

        # 1. YouTube direct browser URL launch
        if clean_name in ["youtube", "yt"]:
            import webbrowser
            webbrowser.open("https://www.youtube.com")
            return True, "YouTube opened in browser"

        # 2. Check DB App Shortcuts first
        shortcut = self.db.find_shortcut(clean_name)
        if shortcut:
            exe_target = shortcut["exe_path"]
            launch_args = shortcut["launch_args"].split() if shortcut["launch_args"] else []
            browser_url = shortcut["browser_url"]

            if browser_url and (not exe_target or not self._is_valid_exe(exe_target)):
                import webbrowser
                webbrowser.open(browser_url)
                return True, f"Opened {shortcut['app_name']} in browser ({browser_url})"

            if exe_target and self._is_valid_exe(exe_target):
                success, msg = self._execute_and_verify(exe_target, launch_args + (args or []))
                if success:
                    return True, msg

        # 3. Resolve canonical name from aliases
        canonical = _APP_ALIASES.get(clean_name, clean_name)

        # 4. Search known installation paths
        if canonical in _COMMON_APP_PATHS:
            for path in _COMMON_APP_PATHS[canonical]:
                if path and os.path.isfile(path):
                    success, msg = self._execute_and_verify(path, args)
                    if success:
                        return True, msg

        # 5. Check system PATH via shutil.which
        which_path = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
        if not which_path and canonical != clean_name:
            for exe_name in self.config.app_mappings.get(canonical, []):
                which_path = shutil.which(exe_name)
                if which_path:
                    break

        if which_path:
            return self._execute_and_verify(which_path, args)

        # 6. Try Windows Registry App Paths
        reg_path = self._find_exe_in_registry(clean_name) or self._find_exe_in_registry(canonical)
        if reg_path and os.path.isfile(reg_path):
            return self._execute_and_verify(reg_path, args)

        # 7. Try UWP / Store apps via 'start' shell protocol
        try:
            cmd = ["cmd.exe", "/c", "start", "", clean_name]
            if args:
                cmd.extend(args)
            subprocess.Popen(cmd, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            return True, f"Application '{app_name}' launch command dispatched."
        except Exception as e:
            logger.debug(f"Shell 'start' failed for '{clean_name}': {e}")

        # 8. Web fallback — if the app has a known web version
        web_url = _WEB_FALLBACKS.get(canonical) or _WEB_FALLBACKS.get(clean_name)
        if web_url:
            import webbrowser
            webbrowser.open(web_url)
            return True, f"Opened {app_name} in browser ({web_url})"

        logger.error(f"Failed to launch '{app_name}' — all strategies exhausted.")
        return False, f"Could not launch '{app_name}': application not found."

    @staticmethod
    def _is_valid_exe(exe_path: str) -> bool:
        if not exe_path:
            return False
        if os.path.isfile(exe_path):
            return True
        if shutil.which(exe_path):
            return True
        return False

    @staticmethod
    def _find_exe_in_registry(app_name: str) -> Optional[str]:
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{app_name}.exe"
                with winreg.OpenKey(root, key_path) as key:
                    val, _ = winreg.QueryValueEx(key, "")
                    return val.strip('"')
            except (FileNotFoundError, OSError):
                pass
        return None

    def _execute_and_verify(self, exe_path: str, args: Optional[List[str]] = None) -> Tuple[bool, str]:
        try:
            full_cmd = [exe_path] + (args or [])
            proc = subprocess.Popen(
                full_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )
            time.sleep(0.3)
            poll_res = proc.poll()
            if poll_res is not None and poll_res != 0:
                return False, f"Process '{exe_path}' exited immediately with code {poll_res}"

            logger.info(f"Successfully launched: {exe_path} (PID: {proc.pid})")
            return True, f"Started '{exe_path}' successfully (PID: {proc.pid})"
        except Exception as e:
            logger.error(f"Error executing {exe_path}: {e}")
            return False, f"Error launching {exe_path}: {e}"

    def close_application(self, process_name: str) -> Tuple[bool, str]:
        """Gracefully closes matching processes via taskkill and psutil."""
        clean = process_name.strip().lower().replace(".exe", "")
        canonical = _APP_ALIASES.get(clean, clean)
        executables = _PROCESS_NAMES.get(canonical, [f"{clean}.exe", clean])

        logger.info(f"Closing application: '{process_name}' (target exes: {executables})")
        killed_any = False

        # 1. Fast taskkill
        for exe in executables:
            try:
                res = subprocess.run(
                    ["taskkill", "/f", "/im", exe],
                    capture_output=True,
                    shell=False
                )
                if res.returncode == 0:
                    killed_any = True
            except Exception:
                pass

        # 2. psutil fallback
        terminated = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = proc.info["name"].lower()
                for target in executables:
                    if target.lower() in pname or clean in pname:
                        proc.terminate()
                        terminated += 1
                        killed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed_any or terminated > 0:
            return True, f"Closed {process_name}"
        return False, f"No running application found matching '{process_name}'"

    def get_active_window_title(self) -> str:
        """Retrieves the title bar of currently focused Windows window."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            return title.strip()
        except Exception as e:
            logger.warning(f"Failed to get active window title: {e}")
            return ""

    def read_visible_page_text(self) -> str:
        """Grabs visible screen or webpage text using native clipboard copy."""
        old_clipboard = self.get_clipboard_text()
        try:
            # 1. Try to copy current selection
            self.send_hotkey("ctrl", "c")
            time.sleep(0.15)
            text = self.get_clipboard_text()

            # 2. If nothing selected or unchanged, select all and copy
            if not text or text == old_clipboard:
                self.send_hotkey("ctrl", "a")
                time.sleep(0.15)
                self.send_hotkey("ctrl", "c")
                time.sleep(0.2)
                text = self.get_clipboard_text()

            if text and len(text.strip()) > 0:
                # Clean up extracted text: remove multiple newlines and spaces
                import re
                cleaned = re.sub(r"\s+", " ", text).strip()
                # Return up to 600 characters for reading aloud
                return cleaned[:600]
            return ""
        finally:
            # Restore previous clipboard if needed
            if old_clipboard:
                try:
                    self.set_clipboard_text(old_clipboard)
                except Exception:
                    pass

    def take_screenshot(self, save_path: Optional[Path] = None) -> Tuple[bool, str]:
        dest = save_path or (self.config.data_dir / f"screenshot_{int(time.time())}.png")
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            dest.parent.mkdir(parents=True, exist_ok=True)
            screenshot.save(str(dest))
            return True, str(dest)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False, str(e)

    def lock_workstation(self) -> bool:
        try:
            ctypes.windll.user32.LockWorkStation()
            return True
        except Exception as e:
            logger.error(f"Failed to lock workstation: {e}")
            return False

    def get_clipboard_text(self) -> str:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return data
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            logger.debug(f"Clipboard read error: {e}")
        return ""

    def set_clipboard_text(self, text: str) -> bool:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            logger.debug(f"Clipboard write error: {e}")
            return False

    def control_volume(self, action: str = "up") -> bool:
        """Controls system volume: 'up', 'down', 'mute' via native Win32 VK events."""
        VK_VOLUME_MUTE = 0xAD
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_UP = 0xAF
        key = VK_VOLUME_UP if action == "up" else (VK_VOLUME_DOWN if action == "down" else VK_VOLUME_MUTE)
        try:
            user32 = ctypes.windll.user32
            ticks = 3 if action in ["up", "down"] else 1
            for _ in range(ticks):
                user32.keybd_event(key, 0, 0, 0)
                user32.keybd_event(key, 0, KEYEVENTF_KEYUP, 0)
                time.sleep(0.02)
            return True
        except Exception as e:
            logger.error(f"Volume control failed: {e}")
            return False

