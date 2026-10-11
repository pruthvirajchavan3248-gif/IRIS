"""
IRIS Offline Brain
Fast, deterministic local rule engine and intent extractor.
Executes Windows commands, app launches, project execution, and social responses
even when the internet or Gemini API is offline.

Supports compound commands like "Notepad kholo aur Hello World likho".
Supports browser tabs, direct typing, closing apps, web search, and webpage reading.
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from ..core.config import get_config
from ..core.logger import get_logger

logger = get_logger("offline_brain")


@dataclass
class OfflineIntentResult:
    matched: bool
    intent: str
    action_type: str
    parameters: Dict[str, Any]
    speech_response: str
    requires_confirmation: bool = False


class OfflineBrain:
    """Offline rule-based intent matching for IRIS."""

    def __init__(self):
        self.config = get_config()

    def parse(self, text: str) -> OfflineIntentResult:
        """Parses user utterance against known offline intents."""
        raw = text.strip()
        lower = raw.lower()

        # Remove "iris" prefix/suffix if present
        clean = re.sub(r"\b(iris|ayris|hey iris|hello iris)\b", "", lower).strip()
        clean = re.sub(r"[^\w\s\.\:\/\-]", "", clean)
        user_name = self.config.user_name

        # ---- COMPOUND COMMANDS: "Notepad kholo aur Hello World likho" ---- #
        compound = self._check_compound_command(clean, user_name)
        if compound:
            return compound

        # ---------------- 1. Browser Tab Controls ---------------- #
        if any(kw in clean for kw in ["tab band karo", "tab close karo", "close tab", "is tab ko band karo", "current tab close"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_control",
                action_type="close_tab",
                parameters={},
                speech_response=f"Current tab close kar diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["naya tab kholo", "new tab", "naya tab", "open new tab", "tab open karo"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_control",
                action_type="new_tab",
                parameters={},
                speech_response=f"Naya browser tab open kar diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["agla tab", "next tab", "tab change karo"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_control",
                action_type="next_tab",
                parameters={},
                speech_response=f"Next tab par switch kar diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["pichla tab", "previous tab", "prev tab"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_control",
                action_type="prev_tab",
                parameters={},
                speech_response=f"Previous tab par switch kar diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["page refresh karo", "refresh karo", "reload karo", "page reload karo"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_control",
                action_type="reload_page",
                parameters={},
                speech_response=f"Webpage refresh kar diya hai, {user_name}."
            )

        # ---------------- 2. Assistant Orb & System Controls ---------------- #
        if any(kw in clean for kw in ["hide ho jao", "chup jao", "hide orb", "hide yourself", "gayab ho jao"]):
            return OfflineIntentResult(
                matched=True,
                intent="orb_control",
                action_type="hide_orb",
                parameters={},
                speech_response=f"Ji {user_name}, main background mein chali jaati hoon. Jab bhi zaroorat ho, kahiye 'IRIS samne aao'."
            )

        if any(kw in clean for kw in ["samne aao", "wapas aao", "show orb", "show yourself", "unhide"]):
            return OfflineIntentResult(
                matched=True,
                intent="orb_control",
                action_type="show_orb",
                parameters={},
                speech_response=f"Ji {user_name}, main samne aa gayi hoon."
            )

        if any(kw in clean for kw in ["mute ho jao", "mute mic", "shant raho", "chup raho", "mute kar do"]):
            return OfflineIntentResult(
                matched=True,
                intent="orb_control",
                action_type="mute_mic",
                parameters={},
                speech_response=f"Microphone mute kar rahi hoon, {user_name}. Unmute karne ke liye tray icon ya keyboard shortcut use karein."
            )

        if any(kw in clean for kw in ["exit", "band ho jao", "close iris", "shutdown iris", "alvida", "bye iris", "bye bye"]):
            return OfflineIntentResult(
                matched=True,
                intent="system_control",
                action_type="exit_app",
                parameters={},
                speech_response=f"Alvida {user_name}! Aapka din shubh rahe."
            )

        # ---------------- Volume & Desktop System Shortcuts ---------------- #
        if any(kw in clean for kw in ["volume badhao", "volume up", "awaz badhao", "aawaz badhao", "sound badhao", "increase volume"]):
            return OfflineIntentResult(
                matched=True,
                intent="system_control",
                action_type="control_volume",
                parameters={"action": "up"},
                speech_response=f"Volume badha diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["volume kam karo", "volume down", "awaz kam karo", "aawaz kam karo", "sound kam karo", "decrease volume"]):
            return OfflineIntentResult(
                matched=True,
                intent="system_control",
                action_type="control_volume",
                parameters={"action": "down"},
                speech_response=f"Volume kam kar diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["volume mute karo", "sound mute karo", "speaker mute karo"]):
            return OfflineIntentResult(
                matched=True,
                intent="system_control",
                action_type="control_volume",
                parameters={"action": "mute"},
                speech_response=f"Volume mute kar diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["screenshot lo", "screenshot le lo", "screen capture", "screenshot khincho", "take screenshot"]):
            return OfflineIntentResult(
                matched=True,
                intent="system_control",
                action_type="take_screenshot",
                parameters={},
                speech_response=f"Screenshot le liya hai, {user_name}."
            )

        if any(kw in clean for kw in ["pc lock karo", "screen lock karo", "computer lock karo", "lock screen", "lock workstation"]):
            return OfflineIntentResult(
                matched=True,
                intent="system_control",
                action_type="lock_workstation",
                parameters={},
                speech_response=f"Workstation lock kar diya hai, {user_name}."
            )

        if any(kw in clean for kw in ["battery kitni hai", "battery status", "charge kitna hai", "battery check karo"]):
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                percent = int(battery.percent)
                plugged = "charging par hai" if battery.power_plugged else "battery par chal raha hai"
                return OfflineIntentResult(
                    matched=True,
                    intent="system_control",
                    action_type="none",
                    parameters={},
                    speech_response=f"Battery {percent} percent hai, aur system {plugged}, {user_name}."
                )

        if any(kw in clean for kw in ["tumhe kisne banaya", "who made you", "who created you", "tumhara creator kaun hai", "tumhe kisne create kiya"]):
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=f"Mujhe Pruthviraj Chavan ne design aur develop kiya hai, ek powerful Windows Virtual Assistant ke roop mein."
            )

        # ---------------- 3. Close/Kill Applications ---------------- #
        close_result = self._check_close_app(clean, user_name)
        if close_result:
            return close_result

        # ---------------- 4. Dictation Mode & Direct Typing ---------------- #
        # "Jo main bolu woh type karo"
        if any(kw in clean for kw in ["jo main bolu woh type karo", "type karo jo main bolu", "dictation on karo", "dictate", "dictation start karo", "dictation mode"]):
            return OfflineIntentResult(
                matched=True,
                intent="dictation_mode",
                action_type="start_dictation",
                parameters={},
                speech_response=f"Ji {user_name}, dictation mode activate kar diya hai. Cursor wali jagah par main type karungi."
            )

        # Direct typing: "type karo Hello World" / "likho Hello World"
        type_match = re.search(r"^(?:likho|type karo|type kar do|type)\s+(.+)$", clean)
        if type_match:
            text_to_type = type_match.group(1).strip()
            if text_to_type and text_to_type not in ["karo", "do", "kuch"]:
                return OfflineIntentResult(
                    matched=True,
                    intent="direct_type",
                    action_type="type_text",
                    parameters={"text": text_to_type},
                    speech_response=f"'{text_to_type}' type kar diya hai, {user_name}."
                )

        # ---------------- 5. Read Visible Webpage / Screen ---------------- #
        if any(kw in clean for kw in ["current webpage padhkar samjhao", "webpage padhkar samjhao", "read webpage", "screen padho", "page padho", "webpage padho", "read page", "screen par kya likha hai"]):
            return OfflineIntentResult(
                matched=True,
                intent="webpage_summary",
                action_type="read_webpage",
                parameters={},
                speech_response=f"Active screen ka text read kar rahi hoon, {user_name}."
            )

        # ---------------- 6. Social Interactions & Greetings ---------------- #
        if any(kw in clean for kw in ["maam ko hello", "mam ko hello", "ma'am ko hello", "madam ko hello"]):
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=f"Namaste Ma'am! Main IRIS hoon, {user_name} ki personal virtual assistant. Aapse milkar bahut khushi hui!"
            )

        if any(kw in clean for kw in ["meri dost hai", "mera dost hai", "dost ko hello", "friend ko hello"]):
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=f"Hello! Main IRIS hoon. {user_name} ke doston se milkar hamesha achha lagta hai. Aap kaise hain?"
            )

        if any(kw in clean for kw in ["apna introduction do", "introduce yourself", "kaun ho tum", "who are you", "apne baare mein batao"]):
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=(
                    "Main IRIS hoon — Intelligent Responsive Interactive System. "
                    "Main aapka personal Windows desktop AI assistant hoon jo voice commands, "
                    "application automation, coding projects aur workflows ko aasani se chalati hoon."
                )
            )

        # Time/date
        if any(kw in clean for kw in ["time kya hai", "kya time hua", "what time", "what is the time", "samay kya hai", "kitne baje"]):
            import datetime
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=f"Abhi {time_str} baj rahe hain, {user_name}."
            )

        if any(kw in clean for kw in ["aaj kya date hai", "date kya hai", "what date", "today date", "aaj ka din"]):
            import datetime
            now = datetime.datetime.now()
            date_str = now.strftime("%d %B %Y, %A")
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=f"Aaj ki date hai {date_str}, {user_name}."
            )

        if any(kw in clean for kw in ["kaise ho", "kaisi ho", "how are you", "kya haal hai", "how do you do"]):
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=f"Main bilkul theek hoon, {user_name}! Aapki seva mein hamesha taiyaar. Bataiye kya kar sakti hoon aapke liye?"
            )

        if any(kw in clean for kw in ["thank you", "thanks", "shukriya", "dhanyavaad", "bahut achha"]):
            return OfflineIntentResult(
                matched=True,
                intent="conversation",
                action_type="none",
                parameters={},
                speech_response=f"Aapka shukriya, {user_name}! Kisi bhi waqt bula lijiyega."
            )

        # ---------------- 7. Project Registry Commands ---------------- #
        run_proj_match = re.search(r"(?:mera\s+)?(.+?)\s+project\s+(?:run|start|chalao)", clean)
        if run_proj_match:
            proj_name = run_proj_match.group(1).strip()
            return OfflineIntentResult(
                matched=True,
                intent="run_project",
                action_type="run_registered_project",
                parameters={"project_name": proj_name},
                speech_response=f"Aapka '{proj_name}' project run kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["kal jo project banaya tha", "recent project", "last project", "kal wala project"]):
            return OfflineIntentResult(
                matched=True,
                intent="open_project",
                action_type="open_registered_project",
                parameters={"recent": True},
                speech_response=f"Aapka recent modified project editor mein open kar rahi hoon, {user_name}."
            )

        # ---------------- 8. Web Search & Browser URLs ---------------- #
        search_result = self._check_web_search(clean, user_name)
        if search_result:
            return search_result

        # YouTube
        if any(kw in clean for kw in ["youtube open karo", "youtube kholo", "open youtube", "youtube chalao"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_search",
                action_type="open_url",
                parameters={"url": "https://www.youtube.com"},
                speech_response=f"YouTube open kar diya hai, {user_name}."
            )

        # ChatGPT
        if any(kw in clean for kw in ["chatgpt open karo", "chatgpt kholo", "open chatgpt"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_search",
                action_type="open_url",
                parameters={"url": "https://chatgpt.com"},
                speech_response=f"ChatGPT open kar rahi hoon, {user_name}."
            )

        # Google
        if any(kw in clean for kw in ["google open karo", "google kholo", "open google"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_search",
                action_type="open_url",
                parameters={"url": "https://www.google.com"},
                speech_response=f"Google open kar rahi hoon, {user_name}."
            )

        # Gmail
        if any(kw in clean for kw in ["gmail open karo", "gmail kholo", "open gmail", "mail kholo"]):
            return OfflineIntentResult(
                matched=True,
                intent="browser_search",
                action_type="open_url",
                parameters={"url": "https://mail.google.com"},
                speech_response=f"Gmail open kar rahi hoon, {user_name}."
            )

        # Translate
        if any(kw in clean for kw in ["english text ko hindi mein translate", "hindi mein translate karo", "translate to hindi"]):
            return OfflineIntentResult(
                matched=True,
                intent="translate_text",
                action_type="translate",
                parameters={"source_lang": "en", "target_lang": "hi"},
                speech_response=f"Text ko Hindi mein translate kar rahi hoon, {user_name}."
            )

        # ---------------- 9. Windows Applications Launch (Specific) ---------------- #
        if any(kw in clean for kw in ["chrome kholo", "chrome open karo", "open chrome", "chrome chalao", "browser kholo", "browser open karo"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "chrome"},
                speech_response=f"Google Chrome open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["whatsapp open karo", "whatsapp kholo", "open whatsapp", "whatsapp chalao"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "whatsapp"},
                speech_response=f"WhatsApp open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["vs code kholo", "vscode kholo", "vs code open karo", "code open karo", "vscode open karo"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "vscode"},
                speech_response=f"VS Code editor open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["notepad kholo", "notepad open karo", "open notepad"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "notepad"},
                speech_response=f"Notepad open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["calculator kholo", "calculator open karo", "calc kholo", "calc open karo", "hisab kholo"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "calculator"},
                speech_response=f"Calculator open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["file explorer kholo", "explorer kholo", "my computer kholo", "files kholo"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "explorer"},
                speech_response=f"File Explorer open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["terminal kholo", "terminal open karo", "powershell kholo", "cmd kholo", "command prompt kholo"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "terminal"},
                speech_response=f"Terminal open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["spotify kholo", "spotify open karo", "spotify chalao"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "spotify"},
                speech_response=f"Spotify open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["settings kholo", "settings open karo", "system settings"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "ms-settings:"},
                speech_response=f"Settings open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["task manager kholo", "task manager open karo"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "taskmgr"},
                speech_response=f"Task Manager open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["paint kholo", "paint open karo", "open paint", "drawing kholo"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "paint"},
                speech_response=f"Paint open kar rahi hoon, {user_name}."
            )

        if any(kw in clean for kw in ["camera kholo", "camera open karo", "open camera"]):
            return OfflineIntentResult(
                matched=True,
                intent="app_launch",
                action_type="launch_app",
                parameters={"app_name": "camera"},
                speech_response=f"Camera open kar rahi hoon, {user_name}."
            )

        # ---------------- 10. Generic App Launch Pattern ---------------- #
        generic_app = re.search(r"([a-zA-Z0-9\s]+?)\s+(?:kholo|open karo|chalao|start karo|launch karo)", clean)
        if generic_app:
            candidate = generic_app.group(1).strip()
            if candidate and len(candidate) > 1 and candidate not in ["project", "mera", "meri", "is", "ye", "yeh", "wo", "woh", "tab", "naya tab"]:
                return OfflineIntentResult(
                    matched=True,
                    intent="app_launch",
                    action_type="launch_app",
                    parameters={"app_name": candidate},
                    speech_response=f"{candidate.capitalize()} open kar rahi hoon, {user_name}."
                )

        return OfflineIntentResult(
            matched=False,
            intent="unknown",
            action_type="none",
            parameters={},
            speech_response=""
        )

    def _check_compound_command(self, clean: str, user_name: str) -> Optional[OfflineIntentResult]:
        """Detects compound commands like 'Notepad kholo aur Hello World likho'."""
        compound_patterns = [
            r"(.+?)\s+(?:kholo|open karo)\s+(?:aur|and|phir)\s+(.+?)\s+(?:likho|type karo|likh do|type kar do)",
            r"(.+?)\s+(?:kholo|open karo)\s+(?:aur|and|phir)\s+(?:usme|usmein|wahan)\s+(.+?)\s+(?:likho|type karo|likh do|type kar do)",
        ]
        for pattern in compound_patterns:
            match = re.search(pattern, clean)
            if match:
                app_name = match.group(1).strip()
                text_to_type = match.group(2).strip()
                logger.info(f"Compound command detected: open '{app_name}' + type '{text_to_type}'")
                return OfflineIntentResult(
                    matched=True,
                    intent="compound_launch_type",
                    action_type="launch_and_type",
                    parameters={"app_name": app_name, "text_to_type": text_to_type},
                    speech_response=f"{app_name.capitalize()} open karke '{text_to_type}' type kar rahi hoon, {user_name}."
                )
        return None

    def _check_close_app(self, clean: str, user_name: str) -> Optional[OfflineIntentResult]:
        """Detects close/kill app commands."""
        close_patterns = [
            r"(.+?)\s+(?:band karo|close karo|bnd karo|kill karo|band kar do|close kar do)",
            r"(?:close|kill|terminate|end)\s+(.+)",
        ]
        for pattern in close_patterns:
            match = re.search(pattern, clean)
            if match:
                app_name = match.group(1).strip()
                if app_name and len(app_name) > 1 and app_name not in ["iris", "is", "ye", "sab", "tab", "current tab"]:
                    return OfflineIntentResult(
                        matched=True,
                        intent="app_close",
                        action_type="close_app",
                        parameters={"app_name": app_name},
                        speech_response=f"{app_name.capitalize()} close kar rahi hoon, {user_name}."
                    )
        return None

    def _check_web_search(self, clean: str, user_name: str) -> Optional[OfflineIntentResult]:
        """Detects flexible web search patterns."""
        search_patterns = [
            (r"google\s+(?:par|pe|mein|me)\s+(.+?)\s+(?:search|khoj)\s*(?:karo|kar do|karna)?", "google"),
            (r"(?:search|find)\s+(.+?)\s+(?:on|in)\s+google", "google"),
            (r"google\s+(?:search\s+)?(?:karo\s+)?(.+?)$", "google"),
            (r"youtube\s+(?:par|pe|mein|me)\s+(.+?)\s+(?:search|khoj)\s*(?:karo|kar do)?", "youtube"),
            (r"(?:search|find)\s+(.+?)\s+(?:on|in)\s+youtube", "youtube"),
            (r"(.+?)\s+(?:search|khoj)\s+karo", "google"),
            (r"(?:search|khoj)\s+(?:for\s+)?(.+?)$", "google"),
        ]
        for pattern, engine in search_patterns:
            match = re.search(pattern, clean)
            if match:
                query = match.group(1).strip()
                if query and len(query) > 1 and query not in ["karo", "kar", "do"]:
                    return OfflineIntentResult(
                        matched=True,
                        intent="browser_search",
                        action_type="web_search",
                        parameters={"query": query, "engine": engine},
                        speech_response=f"{'Google' if engine == 'google' else 'YouTube'} par '{query}' search kar rahi hoon, {user_name}."
                    )
        return None
