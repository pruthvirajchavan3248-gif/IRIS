"""
IRIS Offline Wake-Word Detection Engine
Detects wake phrases including "Hello IRIS", "Hey IRIS", "Utha jao IRIS", "IRIS", and "Wake up IRIS".
Supports Hindi, English, and Hinglish pronunciation variations with phonetic & fuzzy matching.
"""

import re
import difflib
from typing import Optional, List, Tuple
from ..core.config import get_config
from ..core.logger import get_logger

logger = get_logger("wake_word")


class WakeWordDetector:
    """Offline wake phrase matching with multi-variant phonetic tolerance."""

    # Primary recognized patterns
    CANONICAL_PATTERNS = [
        "hello iris",
        "hey iris",
        "utha jao iris",
        "uth jao iris",
        "wake up iris",
        "wake up",
        "utho iris",
        "utha jao",
        "uth jao",
        "hi iris",
        "iris",
        "ayris",
    ]

    # Phonetic and colloquial aliases for "IRIS"
    IRIS_ALIASES = [
        "iris",
        "iriss",
        "ayris",
        "airis",
        "irish",
        "ires",
        "irise",
        "airish",
        "aayris"
    ]

    def __init__(self, custom_phrases: Optional[List[str]] = None):
        self.config = get_config()
        self.phrases = custom_phrases or self.config.wake_phrases
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compiles regex patterns for efficient streaming evaluation."""
        self.regex_patterns = []
        for p in self.CANONICAL_PATTERNS:
            # Replace spaces with flexible whitespace/punctuation
            escaped = re.escape(p).replace(r"\ ", r"[\s\-_]+")
            self.regex_patterns.append(re.compile(rf"\b{escaped}\b", re.IGNORECASE))

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Strips punctuation, normalizes spaces and converts to lowercase."""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.split())

    def check_text(self, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Evaluates a transcribed utterance for wake word occurrence.
        Returns:
            (is_wake_word, matched_phrase, remaining_command)
        """
        if not text:
            return False, None, None

        normalized = self._normalize_text(text)
        words = normalized.split()

        # 1. Direct Regex check against canonical phrases
        for pattern in self.regex_patterns:
            match = pattern.search(normalized)
            if match:
                matched_phrase = match.group(0)
                # Extract remaining command after wake word if user said: "IRIS Chrome kholo"
                remaining = normalized[match.end():].strip()
                logger.info(f"Wake word matched via regex: '{matched_phrase}', remaining command: '{remaining}'")
                return True, matched_phrase, remaining

        # 2. Phonetic Alias Match for standalone IRIS token
        for i, word in enumerate(words):
            if word in self.IRIS_ALIASES:
                prefix = " ".join(words[:i])
                suffix = " ".join(words[i+1:])
                matched = f"{prefix} {word}".strip() if prefix in ["hello", "hey", "hi", "uth", "utha", "wake"] else word
                logger.info(f"Wake word matched via alias: '{matched}', remaining: '{suffix}'")
                return True, matched, suffix

        # 3. Fuzzy Levenshtein match across sliding windows
        window_sizes = [1, 2, 3]
        for w_size in window_sizes:
            for i in range(len(words) - w_size + 1):
                window_str = " ".join(words[i:i + w_size])
                for canonical in self.CANONICAL_PATTERNS:
                    # High similarity check
                    ratio = difflib.SequenceMatcher(None, window_str, canonical).ratio()
                    if ratio >= 0.82:
                        remaining = " ".join(words[i + w_size:]).strip()
                        logger.info(f"Wake word matched via fuzzy ({ratio:.2f}): '{window_str}' -> '{canonical}', remaining: '{remaining}'")
                        return True, window_str, remaining

        return False, None, None

    def get_greeting_response(self, detected_phrase: Optional[str] = None) -> str:
        """
        Returns polite, natural Hindi/Hinglish greeting response.
        Matches requirement: "Ji Sir, IRIS ready hai. Main aapki kya madad kar sakti hoon?"
        """
        phrase = (detected_phrase or "").lower()
        if "uth" in phrase or "wake" in phrase:
            return f"Ji {self.config.user_name}, IRIS ready hai. Bataiye kya karna hai?"
        return f"Ji {self.config.user_name}, IRIS ready hai. Main aapki kya madad kar sakti hoon?"
