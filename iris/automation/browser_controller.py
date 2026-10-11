"""
IRIS Browser Automation & Web Controller
Handles URL opening, search queries on Google/YouTube/ChatGPT,
tab manipulation (new tab, close tab, switch tab), and authorized webpage content extraction.
"""

import urllib.parse
import webbrowser
import requests
from typing import Tuple, Optional
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from ..core.logger import get_logger

logger = get_logger("browser_controller")


class BrowserController:
    """Controls browser navigation, tab shortcuts, and webpage parsing."""

    def open_url(self, url: str) -> bool:
        """Opens URL in system default browser."""
        try:
            logger.info(f"Opening browser URL: {url}")
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Error opening URL {url}: {e}")
            return False

    def search_web(self, query: str, engine: str = "google") -> bool:
        """Performs a web search on Google, YouTube, or Bing."""
        encoded = urllib.parse.quote_plus(query)
        if engine.lower() == "youtube":
            url = f"https://www.youtube.com/results?search_query={encoded}"
        elif engine.lower() == "chatgpt":
            url = f"https://chatgpt.com/?q={encoded}"
        else:
            url = f"https://www.google.com/search?q={encoded}"

        return self.open_url(url)

    def close_tab(self, win_ctrl) -> bool:
        """Closes the current browser tab (Ctrl+W)."""
        logger.info("Closing active browser tab (Ctrl+W)")
        return win_ctrl.send_hotkey("ctrl", "w")

    def new_tab(self, win_ctrl) -> bool:
        """Opens a new browser tab (Ctrl+T)."""
        logger.info("Opening new browser tab (Ctrl+T)")
        return win_ctrl.send_hotkey("ctrl", "t")

    def next_tab(self, win_ctrl) -> bool:
        """Switches to the next browser tab (Ctrl+Tab)."""
        logger.info("Switching to next browser tab (Ctrl+Tab)")
        return win_ctrl.send_hotkey("ctrl", "tab")

    def previous_tab(self, win_ctrl) -> bool:
        """Switches to the previous browser tab (Ctrl+Shift+Tab)."""
        logger.info("Switching to previous browser tab (Ctrl+Shift+Tab)")
        return win_ctrl.send_hotkey("ctrl", "shift", "tab")

    def reload_page(self, win_ctrl) -> bool:
        """Reloads active browser page (F5)."""
        logger.info("Reloading active webpage (F5)")
        return win_ctrl.send_hotkey("f5")

    def fetch_webpage_content(self, url: str) -> Tuple[bool, str]:
        """Fetches clean text body from a URL for AI summarization."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) IRIS-Assistant/1.0"
            }
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code != 200:
                return False, f"HTTP Error {resp.status_code}"

            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                for s in soup(["script", "style", "noscript", "header", "footer"]):
                    s.decompose()
                text = soup.get_text(separator=" ", strip=True)
            except Exception:
                import re
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = " ".join(text.split())

            return True, text[:3000]

        except Exception as e:
            logger.error(f"Failed to fetch webpage content: {e}")
            return False, str(e)
