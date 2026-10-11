Set WshShell = CreateObject("WScript.Shell")
' Run IRIS Supervisor silently without console window (0 = hide window)
WshShell.CurrentDirectory = "C:\Users\Dell\Documents\New folder"
WshShell.Run """C:\Users\Dell\AppData\Local\Programs\Python\Python312\pythonw.exe"" iris_watchdog.py", 0, False
