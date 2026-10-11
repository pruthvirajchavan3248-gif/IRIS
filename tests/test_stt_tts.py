"""
Unit Tests for Speech Recognition and Voice Synthesis Logic
"""

import pytest
from iris.speech.stt import SpeechToTextEngine
from iris.speech.tts import TextToSpeechEngine


def test_language_detection_heuristics():
    # Hindi Devanagari
    assert SpeechToTextEngine._detect_language_heuristic("नमस्ते आईरिस, आप कैसी हैं?") == "hi"

    # Hinglish
    assert SpeechToTextEngine._detect_language_heuristic("Chrome kholo aur mera project chalao") == "hinglish"
    assert SpeechToTextEngine._detect_language_heuristic("IRIS ma'am ko hello bolo") == "hinglish"
    assert SpeechToTextEngine._detect_language_heuristic("Utha jao IRIS") == "hinglish"

    # Pure English
    assert SpeechToTextEngine._detect_language_heuristic("Open the browser and show latest news") == "en"


def test_tts_voice_selection():
    tts = TextToSpeechEngine()

    # Hindi script should select SwaraNeural
    assert "Swara" in tts.select_voice_for_text("नमस्ते सर")

    # Hinglish text should select SwaraNeural
    assert "Swara" in tts.select_voice_for_text("Ji Sir, main ready hoon. Bataiye kya karna hai?")

    # English text should select NeerjaNeural
    assert "Neerja" in tts.select_voice_for_text("Hello Sir, how can I assist you today?")


def test_rust_audio_bridge():
    from iris.speech.rust_audio_bridge import calculate_pcm_rms
    samples = [1000, -1000, 1000, -1000]
    rms = calculate_pcm_rms(samples)
    assert abs(rms - 1000.0) < 1.0

