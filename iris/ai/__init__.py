"""
IRIS AI Reasoning Subsystem
Google Gemini API integration, offline natural language rule engine,
intent classifier, and conversational memory.
"""

from .gemini_client import GeminiClient
from .intent_engine import IntentEngine, ResolvedIntent
from .offline_brain import OfflineBrain
from .system_prompts import IRIS_SYSTEM_PROMPT

__all__ = [
    "GeminiClient",
    "IntentEngine",
    "ResolvedIntent",
    "OfflineBrain",
    "IRIS_SYSTEM_PROMPT",
]
