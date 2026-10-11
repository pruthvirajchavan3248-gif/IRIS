"""
IRIS Windows Startup Manager
Manages Windows startup registry entries and silent launcher VBScript.
Ensures IRIS starts in the background after login without opening a command prompt window.
"""

import os
import sys
import winreg
from pathlib import Path
from typing import Tuple

from ..core.config import get_config
from ..core.logger import get_logger

logger = get_logger("startup")

REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "IRISVirtualAssistant"


class WindowsStartupManager:
    """Manages silent auto-start for IRIS upon user login."""

    def __init__(self):
        self.config = get_config()
        self.vbs_launcher = self.config.base_dir / "iris_runner.vbs"
        self._ensure_vbs_launcher()

    def _ensure_vbs_launcher(self) -> Path:
        """Generates silent VBScript launcher if not already created."""
        py_exe = Path(sys.executable)
        pyw_exe = py_exe.parent / "pythonw.exe"
        runner_exe = str(pyw_exe) if pyw_exe.exists() else str(py_exe)

        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
' Run IRIS silently without console window (0 = hide window)
WshShell.CurrentDirectory = "{self.config.base_dir}"
WshShell.Run """{runner_exe}"" -m iris.main", 0, False
'''
        self.vbs_launcher.write_text(vbs_content, encoding="utf-8")
        return self.vbs_launcher

    def is_autostart_enabled(self) -> bool:
        """Checks if IRIS is registered in Windows Startup registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(val)
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"Error checking registry startup: {e}")
            return False

    def enable_autostart(self) -> Tuple[bool, str]:
        """Registers silent VBScript launcher in Windows Run registry."""
        try:
            self._ensure_vbs_launcher()
            target_cmd = f'wscript.exe "{self.vbs_launcher}"'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, target_cmd)
            logger.info("Auto-start registered in Windows HKCU Run key.")
            return True, "Auto-start enabled successfully."
        except Exception as e:
            logger.error(f"Failed to enable auto-start: {e}")
            return False, str(e)

    def disable_autostart(self) -> Tuple[bool, str]:
        """Removes IRIS from Windows Startup registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, APP_NAME)
            logger.info("Auto-start removed from Windows HKCU Run key.")
            return True, "Auto-start disabled successfully."
        except FileNotFoundError:
            return True, "Already disabled."
        except Exception as e:
            logger.error(f"Failed to disable auto-start: {e}")
            return False, str(e)
