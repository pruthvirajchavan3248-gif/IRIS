@echo off
title IRIS Virtual Assistant
cd /d "%~dp0"

echo ===================================================
echo     Launching IRIS (Intelligent Responsive System)
echo ===================================================

REM Detect Python executable (checking real installation path first)
set "PYTHON_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "C:\Python312\python.exe" (
    set "PYTHON_EXE=C:\Python312\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        python --version >nul 2>nul
        if %errorlevel% equ 0 (
            set "PYTHON_EXE=python"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found in PATH or standard installation directory.
    echo Please install Python 3.12+ or add it to system PATH.
    pause
    exit /b 1
)

echo [INFO] Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" -m iris.main
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] IRIS terminated unexpectedly with error code %errorlevel%.
    pause
)
