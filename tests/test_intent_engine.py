"""
Unit Tests for Intent Engine, Offline Brain, and Wake Word Matching
"""

import pytest
from iris.ai.offline_brain import OfflineBrain
from iris.speech.wake_word import WakeWordDetector


def test_wake_word_variations():
    """Validates wake phrases in English, Hindi, and Hinglish."""
    detector = WakeWordDetector()

    # 1. "Hello IRIS"
    matched, phrase, rem = detector.check_text("hello iris")
    assert matched is True

    # 2. "Hey IRIS"
    matched, phrase, rem = detector.check_text("hey iris")
    assert matched is True

    # 3. "Utha jao IRIS"
    matched, phrase, rem = detector.check_text("utha jao iris")
    assert matched is True
    assert "Bataiye kya karna hai" in detector.get_greeting_response(phrase)

    # 4. "Wake up IRIS"
    matched, phrase, rem = detector.check_text("wake up iris")
    assert matched is True

    # 5. Combined utterance: "IRIS Chrome kholo"
    matched, phrase, rem = detector.check_text("iris chrome kholo")
    assert matched is True
    assert "chrome kholo" in rem.lower()


def test_offline_brain_app_launches():
    brain = OfflineBrain()

    # Chrome
    res = brain.parse("IRIS Chrome kholo")
    assert res.matched is True
    assert res.action_type == "launch_app"
    assert res.parameters.get("app_name") == "chrome"

    # WhatsApp
    res = brain.parse("WhatsApp open karo")
    assert res.matched is True
    assert res.action_type == "launch_app"
    assert res.parameters.get("app_name") == "whatsapp"

    # VS Code
    res = brain.parse("VS Code kholo")
    assert res.matched is True
    assert res.action_type == "launch_app"
    assert res.parameters.get("app_name") == "vscode"


def test_offline_brain_browser_searches():
    brain = OfflineBrain()

    # YouTube
    res = brain.parse("YouTube open karo")
    assert res.matched is True
    assert res.action_type == "open_url"
    assert "youtube.com" in res.parameters.get("url")

    # ChatGPT
    res = brain.parse("ChatGPT open karo")
    assert res.matched is True
    assert res.action_type == "open_url"
    assert "chatgpt.com" in res.parameters.get("url")

    # Google Search
    res = brain.parse("Google par AI search karo")
    assert res.matched is True
    assert res.action_type == "web_search"
    assert res.parameters.get("query") == "ai"


def test_offline_brain_dictation_and_projects():
    brain = OfflineBrain()

    # Dictation
    res = brain.parse("Jo main bolu woh type karo")
    assert res.matched is True
    assert res.action_type == "start_dictation"

    # Run Project
    res = brain.parse("Mera Level Up project run karo")
    assert res.matched is True
    assert res.action_type == "run_registered_project"
    assert res.parameters.get("project_name") == "level up"

    # Open recent project
    res = brain.parse("Maine kal jo project banaya tha use open karo")
    assert res.matched is True
    assert res.action_type == "open_registered_project"
    assert res.parameters.get("recent") is True


def test_offline_brain_orb_controls():
    brain = OfflineBrain()

    assert brain.parse("IRIS hide ho jao").action_type == "hide_orb"
    assert brain.parse("IRIS samne aao").action_type == "show_orb"
    assert brain.parse("IRIS mute ho jao").action_type == "mute_mic"
    assert brain.parse("IRIS exit").action_type == "exit_app"


def test_offline_brain_social():
    brain = OfflineBrain()

    # Ma'am hello
    res = brain.parse("IRIS ma'am ko hello bolo")
    assert res.matched is True
    assert "Ma'am" in res.speech_response

    # Friend hello
    res = brain.parse("IRIS ye meri dost hai, hello bolo")
    assert res.matched is True
    assert "doston" in res.speech_response.lower()

    # Introduction
    res = brain.parse("IRIS apna introduction do")
    assert res.matched is True
    assert "Intelligent Responsive Interactive System" in res.speech_response
