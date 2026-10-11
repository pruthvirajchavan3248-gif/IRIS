"""
IRIS Google Gemini AI Client
Interacts with Google Gemini models for conversational reasoning, intent extraction,
and structured desktop automation planning.
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from ..core.config import get_config
from ..core.logger import get_logger
from .system_prompts import IRIS_SYSTEM_PROMPT

logger = get_logger("gemini")


class GeminiClient:
    """Google Gemini AI integration supporting SDK and REST fallback with HTTP keep-alive pooling."""

    def __init__(self, api_key: Optional[str] = None):
        self.config = get_config()
        self.api_key = api_key or self.config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = self.config.gemini_model
        self.fallback_model = self.config.gemini_fallback_model
        self._sdk_client = None
        self._session = requests.Session()  # Connection pooling avoids SSL/TCP handshake latency
        self._init_client()

    def _init_client(self) -> None:
        """Initializes google-genai client if API key is present."""
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY detected. Online reasoning will use offline brain fallback.")
            return

        try:
            from google import genai
            self._sdk_client = genai.Client(api_key=self.api_key)
            logger.info("Google GenAI client initialized successfully.")
        except Exception as e:
            logger.info(f"Using REST API fallback for Gemini: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def generate_response(self, user_prompt: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Sends conversation to Gemini and parses the structured JSON plan.
        Returns dictionary containing:
            - speech_response
            - intent
            - action
            - requires_confirmation
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "API_KEY_MISSING",
                "speech_response": ""
            }

        # 1. Direct REST via pooled HTTP session is fastest and lowest overhead
        rest_result = self._rest_generate_content(user_prompt, conversation_history)
        if rest_result.get("success"):
            return rest_result

        # 2. Try SDK fallback if available
        if self._sdk_client:
            try:
                contents = []
                contents.append(f"SYSTEM INSTRUCTIONS:\n{IRIS_SYSTEM_PROMPT}")

                if conversation_history:
                    for turn in conversation_history[-4:]:
                        role = "user" if turn.get("role") == "user" else "model"
                        contents.append(f"{role.upper()}: {turn.get('text', '')}")

                contents.append(f"USER: {user_prompt}\nASSISTANT:")

                response = self._sdk_client.models.generate_content(
                    model=self.model_name,
                    contents="\n\n".join(contents),
                )

                parsed = self._extract_json(response.text)
                if parsed:
                    parsed["success"] = True
                    return parsed
            except Exception as e:
                logger.warning(f"SDK inference failed on {self.model_name}: {e}")

        return rest_result

    def _rest_generate_content(self, user_prompt: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Direct HTTPS call to Google Generative Language API endpoint with connection pooling."""
        # Use fastest models list
        models_to_try = [self.model_name, self.fallback_model, "gemini-flash-lite-latest"]
        # Deduplicate preserving order
        seen = set()
        unique_models = []
        for m in models_to_try:
            if m and m not in seen:
                seen.add(m)
                unique_models.append(m)

        # Build contents payload
        messages = []
        if conversation_history:
            for turn in conversation_history[-4:]:
                role = "user" if turn.get("role") == "user" else "model"
                messages.append({"role": role, "parts": [{"text": turn.get("text", "")}]})

        messages.append({"role": "user", "parts": [{"text": user_prompt}]})

        payload = {
            "system_instruction": {
                "parts": [{"text": IRIS_SYSTEM_PROMPT}]
            },
            "contents": messages,
            "generationConfig": {
                "temperature": self.config.ai_temperature,
                "maxOutputTokens": self.config.max_tokens,
                "response_mime_type": "application/json"
            }
        }

        for model in unique_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                resp = self._session.post(url, json=payload, timeout=4.0)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = self._extract_json(text)
                        if parsed:
                            parsed["success"] = True
                            return parsed
                else:
                    logger.warning(f"REST API model {model} returned status {resp.status_code}")
            except requests.exceptions.Timeout:
                logger.warning(f"REST API timeout on model {model}")
            except Exception as e:
                logger.warning(f"Network error on REST API {model}: {e}")

        return {
            "success": False,
            "error": "ALL_MODELS_FAILED",
            "speech_response": ""
        }

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Cleans and extracts JSON object from response markdown."""
        if not text:
            return None
        clean = text.strip()
        # Remove ```json fences
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            return json.loads(clean)
        except Exception:
            # Try finding curly braces
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(clean[start:end+1])
                except Exception:
                    pass
        return None
