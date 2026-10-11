# IRIS — Intelligent Responsive Interactive System
### Advanced Windows AI Virtual Assistant

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue.svg)](https://microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.12%2B-brightgreen.svg)](https://python.org)
[![GUI](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt-cyan.svg)](https://qt.io)
[![Voice](https://img.shields.io/badge/TTS-Edge--TTS%20Neural-purple.svg)](https://github.com/rany2/edge-tts)
[![Brain](https://img.shields.io/badge/AI-Google%20Gemini%202.5-orange.svg)](https://aistudio.google.com/)

---

## 🌟 Overview

**IRIS (Intelligent Responsive Interactive System)** is a production-grade, native Windows Virtual AI Assistant designed to run silently in the background, awaken on custom offline wake phrases, interact with a natural female voice, and seamlessly control Windows applications, typing dictation, developer projects, and system settings.

Unlike conventional chatbot web applications, IRIS features a **futuristic floating holographic AI Orb widget** that docks cleanly in any screen corner, renders glowing state-reactive visual effects, provides full Windows system tray privacy controls, and manages an integrated SQLite memory database.

---

## 🛠️ Architecture & Tech Stack

```
IRIS Assistant Architecture:
┌────────────────────────────────────────────────────────────────────────┐
│                        USER VOICE & DESKTOP INTERACTION                │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  ▼
┌───────────────────────────────┐   ┌────────────────────────────────────┐
│   FLOATING HOLOGRAPHIC ORB    │   │         AUDIO PIPELINE             │
│   • Frameless Qt/PySide6      │   │   • VAD & Noise Calibration        │
│   • Draggable Position        │◄──┤   • Offline Wake-Word Listener     │
│   • State Reactive Rings      │   │   • Hindi / English / Hinglish STT │
│   • System Tray Privacy Menu  │   │   • Edge-TTS Female Neural Voice   │
└───────────────┬───────────────┘   └─────────────────┬──────────────────┘
                │                                     │
                ▼                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   CENTRAL DISPATCHER & EVENT BUS                       │
├───────────────────────────────────┬────────────────────────────────────┤
│   OFFLINE INTENT BRAIN            │   ONLINE GEMINI REASONING          │
│   • Zero-latency local rules      │   • Google Gemini 2.5 Flash        │
│   • App launches, system commands │   • Deep contextual conversations  │
│   • Social greetings & dialogs    │   • Code explanation & reasoning   │
└─────────────────┬─────────────────┴─────────────────┬──────────────────┘
                  │                                   │
                  ▼                                   ▼
┌───────────────────────────────────┐   ┌────────────────────────────────┐
│      AUTOMATION & CONTROLLERS     │   │      MEMORY & DATABASE         │
│   • WindowsController (PyWin32)   │   │   • SQLite WAL Mode            │
│   • DictationManager (Keystrokes) │◄──┤   • User Preferences           │
│   • ProjectRunner (Tech Detect)   │   │   • Project Registry           │
│   • BrowserController (Search)    │   │   • App Shortcuts & History    │
│   • SecurityGuard (Safe Sandbox)  │   │   • Dashboard Memory Viewer    │
└───────────────────────────────────┘   └────────────────────────────────┘
```

- **Python 3.12+**: Asynchronous core, system automation, and event engine.
- **PySide6 / Qt**: Holographic floating orb, glassmorphism dashboard, and system tray.
- **Google Gemini API**: Reasoning engine (`gemini-2.5-flash`, `gemini-1.5-flash`).
- **Edge TTS**: Neural natural female voice (`hi-IN-SwaraNeural`, `en-IN-NeerjaNeural`, `en-US-JennyNeural`) with offline Windows SAPI5 (`pyttsx3`) fallback.
- **Speech Recognition**: Multi-engine supporting Hindi, English, and Hinglish with energy auto-calibration.
- **PyWin32 + PyWinAuto**: Windows application control, focus management, and Unicode keystroke injection.
- **Rust Audio Module**: Optional high-performance C-ABI audio DSP ring buffer and RMS energy engine (`rust_core/`).
- **SQLite Database**: Local memory, project registry, app shortcuts, conversation history, and privacy management.

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- Windows 10 or 11 (64-bit)
- Python 3.12+ installed and added to PATH
- Working microphone and audio output

### 2. Install Dependencies
Open PowerShell or Command Prompt in the project folder and run:
```powershell
pip install -r requirements.txt
```

### 3. Configure API Key
Copy the `.env.example` file to `.env`:
```powershell
copy .env.example .env
```
Open `.env` and add your Google Gemini API key:
```ini
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
IRIS_USER_NAME=Sir
```
*(Note: IRIS operates its full offline command engine even without an API key!)*

### 4. Run IRIS
- **Normal Launch (Console Output):**
  ```powershell
  python -m iris.main
  ```
  *or double-click `start_iris.bat`.*

- **Silent Background Launch (No Console Window):**
  Double-click `iris_runner.vbs`. IRIS will run silently in the system tray and floating orb without opening a terminal window.

---

## 🎙️ Wake Words & Voice Commands

### 1. Offline Wake Phrases
Say any of the following to activate IRIS:
- `"Hello IRIS"`
- `"Hey IRIS"`
- `"Utha jao IRIS"` *(Response: "Ji Sir, IRIS ready hai. Bataiye kya karna hai?")*
- `"IRIS"`
- `"Wake up IRIS"`

---

### 2. Windows Applications & Desktop Control
| Voice Command (Hindi / English / Hinglish) | Executed Action |
|---|---|
| `"IRIS Chrome kholo."` | Launches Google Chrome |
| `"WhatsApp open karo."` | Launches WhatsApp (or opens WhatsApp Web fallback) |
| `"VS Code kholo."` | Launches Visual Studio Code |
| `"YouTube open karo."` | Opens YouTube in default browser |
| `"ChatGPT open karo."` | Opens ChatGPT in default browser |
| `"Google par AI search karo."` | Performs web search on Google for "AI" |

---

### 3. Typing Dictation Mode
- **Activate:** `"Jo main bolu woh type karo."`
- **Behavior:** IRIS enters dictation mode and injects your spoken words directly into whatever input field or text editor currently has cursor focus using native Windows Unicode SendInput.
- **Deactivate:** Say `"Stop typing"` or `"Dictation band karo"`.

---

### 4. Coding Project Execution & Registry
IRIS maintains an intelligent registry of your coding projects with tech stack detection (Python, Node.js, Next.js, Rust, Go, etc.) and approved run commands:
- `"Mera Level Up project run karo."` → Identifies "Level Up" from registry, runs approved command (e.g. `npm run dev` or `cargo run`).
- `"Maine kal jo project banaya tha use open karo."` → Detects most recently modified project directory on disk and opens it in VS Code.

---

### 5. Floating Orb & Privacy Controls
| Command | Action |
|---|---|
| `"IRIS hide ho jao"` | Hides floating orb into background system tray |
| `"IRIS samne aao"` | Restores floating orb onto the desktop |
| `"IRIS mute ho jao"` | Mutes microphone listening (Privacy mode) |
| `"IRIS exit"` | Safely terminates application and background threads |

---

### 6. Social Dialogues & Natural Conversation
- `"IRIS ma'am ko hello bolo."` → *"Namaste Ma'am! Main IRIS hoon, Sir ki virtual assistant..."*
- `"IRIS ye meri dost hai, hello bolo."` → *"Hello! Main IRIS hoon. Sir ke doston ka hamesha swagat hai..."*
- `"IRIS apna introduction do."` → Explains identity, features, and capabilities.
- `"IRIS mujhe Java programming samjhao."` → Clear, respectful explanation generated via Gemini AI reasoning.
- `"IRIS mera code explain karo."` → Analyzes clipboard or provided snippet.

---

## 🔮 Floating Orb States

The floating holographic orb reflects IRIS's real-time state with distinct animated visual rings:

| Orb State | Color Theme | Description |
|---|---|---|
| **Idle** | Cyan / Electric Blue Pulse | Passive background listening mode |
| **Listening** | Vibrant Magenta / Neon Violet Rings | User speaking; active Voice Activity Detection |
| **Thinking** | Amber / Gold Orbital Arcs | Processing intent and AI reasoning |
| **Speaking** | Emerald / Aquamarine Wave Ripples | Edge-TTS neural female voice active |
| **Muted** | Charcoal Slate Gray | Microphone privacy mute active |
| **Error** | Crimson Red Alert | Temporary diagnostic alert |

- **Left-Click Drag:** Move the orb anywhere across screens.
- **Left-Click Tap:** Activate listening immediately.
- **Right-Click:** Open context menu (Mute/Unmute, Memory Viewer, Hide Orb, Exit).

---

## 🗄️ Memory & Settings Dashboard

Open the dashboard anytime by right-clicking the orb or double-clicking the system tray icon:
1. **Memory & Database:** Live SQLite storage statistics (KB/MB), view tables (`conversation_history`, `command_history`, `user_preferences`, `registered_projects`, `app_shortcuts`), filter records, export memory to JSON, and clear histories for privacy.
2. **Project Registry:** Add developer projects, browse folder paths, auto-detect technology stacks, configure approved run commands, and test run projects.
3. **App Shortcuts:** Map custom spoken aliases to executables or web URLs.
4. **Voice & Audio:** Choose Edge-TTS female voices, adjust speaking rate and pitch, preview voice samples, and select microphone devices.
5. **General & Security:** Configure salutation name, Google Gemini API key, AI model selection, destructive action confirmation, and Windows startup.

---

## 🚀 Windows Startup Configuration

To launch IRIS automatically after Windows login without a command prompt terminal:
1. Open **Memory & Settings Dashboard** → **General & Security**.
2. Check **"Start IRIS automatically on Windows login (Background mode without terminal)"**.
3. Click **Save Settings**.
IRIS will register `iris_runner.vbs` in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

---

## 📦 PyInstaller Standalone Executable Packaging

To build a standalone Windows executable (`IRIS.exe`):
```powershell
pip install pyinstaller
python build_exe.py
```
The compiled output will be generated in `dist/IRIS/IRIS.exe`.

---

## 🧪 Running Automated Tests

Run the full automated test suite (23 unit & integration tests):
```powershell
pytest tests/ -v
```
All tests validate SQLite schemas, offline brain intent parsing, project registry fuzzy matching, security command guards, voice selection heuristics, and dictation activation.

---

## 🔒 Security & Privacy Notice

- **API Keys:** Never hardcoded. Loaded strictly via `.env` or user settings.
- **Dangerous Commands:** High-risk actions (`format`, `rmdir /s /q`, `diskpart`, `reg delete`, encoded powershell) are blocked by the `SecurityGuard`.
- **Acoustic Feedback Prevention:** The audio manager automatically suppresses microphone processing while TTS is speaking to prevent self-triggering feedback loops.
- **Microphone Privacy:** Muting IRIS stops all audio buffer parsing immediately.
