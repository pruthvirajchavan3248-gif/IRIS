@echo off
title IRIS Background Launcher
cd /d "%~dp0"
echo Starting IRIS 24/7 background service...
wscript.exe "%~dp0iris_runner.vbs"
echo IRIS is now running continuously in the background!
timeout /t 3 >nul
exit
