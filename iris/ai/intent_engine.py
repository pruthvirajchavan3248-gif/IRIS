"""
IRIS Intent Classification & Reasoning Engine
Routes incoming speech commands between fast Offline Rule Brain and Gemini AI reasoning.
Maintains session conversational memory and structured action definitions.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import uuid

from ..core.config import get_config
from ..core.logger import get_logger
from ..database.db import get_db
from .offline_brain import OfflineBrain, OfflineIntentResult
from .gemini_client import GeminiClient

logger = get_logger("intent_engine")


@dataclass
class ResolvedIntent:
    user_utterance: str
    intent: str
    action_type: str
    parameters: Dict[str, Any]
    speech_response: str
    requires_confirmation: bool
    source: str  # "offline_brain" | "gemini_ai" | "fallback"


class IntentEngine:
    """Orchestrates natural language intent classification and AI reasoning."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.config = get_config()
        self.db = get_db()
        self.offline_brain = OfflineBrain()
        self.gemini = gemini_client or GeminiClient()
        self.current_session_id = str(uuid.uuid4())[:8]

    def resolve(self, utterance: str, language: str = "hinglish") -> ResolvedIntent:
        """
        Resolves user utterance into an actionable intent and speech response.
        1. Checks offline fast rule brain first.
        2. If unmatched or conversational/complex, passes to Gemini AI reasoning.
        3. If offline/error, provides graceful conversational fallback.
        """
        logger.info(f"Resolving intent for: '{utterance}' (Language: {language})")

        # Log user message to conversation memory
        self.db.log_conversation(
            session_id=self.current_session_id,
            role="user",
            text=utterance,
            language=language
        )

        # 1. Offline rule match for immediate responsiveness and offline operation
        offline_res: OfflineIntentResult = self.offline_brain.parse(utterance)
        if offline_res.matched:
            logger.info(f"Resolved via offline brain: {offline_res.intent} -> {offline_res.action_type}")
            
            # Log IRIS response to memory
            self.db.log_conversation(
                session_id=self.current_session_id,
                role="iris",
                text=offline_res.speech_response,
                language=language,
                intent=offline_res.intent
            )

            return ResolvedIntent(
                user_utterance=utterance,
                intent=offline_res.intent,
                action_type=offline_res.action_type,
                parameters=offline_res.parameters,
                speech_response=offline_res.speech_response,
                requires_confirmation=offline_res.requires_confirmation,
                source="offline_brain"
            )

        # 2. Online Gemini AI Reasoning
        if self.gemini.is_configured():
            recent_convs = self.db.get_recent_conversations(limit=6)
            ai_res = self.gemini.generate_response(utterance, recent_convs)

            if ai_res.get("success", False):
                speech_resp = ai_res.get("speech_response", "Ji Sir, samajh gayi.")
                intent = ai_res.get("intent", "conversation")
                action = ai_res.get("action", {})
                action_type = action.get("type", "none")
                params = action.get("parameters", {})
                req_conf = ai_res.get("requires_confirmation", False)

                logger.info(f"Resolved via Gemini: {intent} -> {action_type}")

                self.db.log_conversation(
                    session_id=self.current_session_id,
                    role="iris",
                    text=speech_resp,
                    language=language,
                    intent=intent
                )

                return ResolvedIntent(
                    user_utterance=utterance,
                    intent=intent,
                    action_type=action_type,
                    parameters=params,
                    speech_response=speech_resp,
                    requires_confirmation=req_conf,
                    source="gemini_ai"
                )

        # 3. Fallback when not matched and offline/no API key
        user_name = self.config.user_name
        fallback_speech = f"Maaf kijiyega {user_name}, main ise poori tarah samajh nahi paayi. Kya aap dobara bata sakte hain?"
        
        self.db.log_conversation(
            session_id=self.current_session_id,
            role="iris",
            text=fallback_speech,
            language=language,
            intent="unknown"
        )

        return ResolvedIntent(
            user_utterance=utterance,
            intent="unknown",
            action_type="none",
            parameters={},
            speech_response=fallback_speech,
            requires_confirmation=False,
            source="fallback"
        )
