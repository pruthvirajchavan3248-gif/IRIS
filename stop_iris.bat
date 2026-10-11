@echo off
title Stop IRIS Virtual Assistant
cd /d "%~dp0"
echo ===================================================
echo     Terminating IRIS Assistant & Watchdog
echo ===================================================

REM Signal watchdog to stop permanently
type nul > "%~dp0.stop_iris"

REM Kill any running watchdog supervisor and iris processes
taskkill /f /fi "WINDOWTITLE eq IRIS*" >nul 2>&1
wmic process where "commandline like '%%iris_watchdog%%' or commandline like '%%iris.main%%'" delete >nul 2>&1
powershell -Command "Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'iris' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo [INFO] IRIS background assistant stopped successfully.
timeout /t 2 >nul
