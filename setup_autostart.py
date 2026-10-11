import os
import shutil
import winreg
from pathlib import Path

vbs = Path(r"c:\Users\Dell\Documents\New folder\iris_runner.vbs").resolve()
cmd = f'wscript.exe "{vbs}"'

# 1. Registry Run Key
key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
    winreg.SetValueEx(k, "IRISVirtualAssistant", 0, winreg.REG_SZ, cmd)
print("Registry HKCU Run key set to:", cmd)

# 2. Windows Startup folder
appdata = os.environ.get("APPDATA", "")
startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
if startup_dir.exists():
    dest = startup_dir / "IRIS_Runner.vbs"
    shutil.copy2(vbs, dest)
    print("Startup folder launcher copied to:", dest)
else:
    print("Startup folder not found:", startup_dir)

print("PERMANENT AUTOSTART CONFIGURED SUCCESSFULLY!")
