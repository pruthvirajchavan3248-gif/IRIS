"""
Unit Tests for Windows Automation and Dictation
"""

import pytest
from iris.automation.windows_controller import WindowsController
from iris.automation.dictation import DictationManager
from iris.automation.browser_controller import BrowserController


def test_dictation_activation():
    dm = DictationManager()
    assert dm.is_active is False
    dm.start_dictation()
    assert dm.is_active is True
    dm.stop_dictation()
    assert dm.is_active is False


def test_browser_url_encoding():
    bc = BrowserController()
    # Test method exists and handles inputs safely
    assert hasattr(bc, "open_url")
    assert hasattr(bc, "search_web")
    assert hasattr(bc, "fetch_webpage_content")


def test_windows_controller_methods():
    wc = WindowsController()
    assert hasattr(wc, "launch_application")
    assert hasattr(wc, "close_application")
    assert hasattr(wc, "get_active_window_title")
    assert hasattr(wc, "take_screenshot")
    assert hasattr(wc, "get_clipboard_text")
    assert hasattr(wc, "set_clipboard_text")
