"""
Unit Tests for Security Guard & Command Validator
"""

import pytest
from iris.automation.security import SecurityGuard


def test_dangerous_shell_command_blocking():
    guard = SecurityGuard()

    # Blocked commands
    assert guard.validate_command_string("format c:")[0] is False
    assert guard.validate_command_string("rmdir /s /q C:\\Windows")[0] is False
    assert guard.validate_command_string("del /f /s /q *.*")[0] is False
    assert guard.validate_command_string("reg delete HKLM\\Software")[0] is False
    assert guard.validate_command_string("powershell -encodedcommand dGVzdA==")[0] is False

    # Allowed safe commands
    assert guard.validate_command_string("python main.py")[0] is True
    assert guard.validate_command_string("npm run dev")[0] is True
    assert guard.validate_command_string("cargo run --release")[0] is True
    assert guard.validate_command_string("code .")[0] is True


def test_action_validation_and_confirmation():
    guard = SecurityGuard()

    # Normal action
    allowed, conf, msg = guard.validate_action("launch_app", {"app_name": "chrome"})
    assert allowed is True
    assert conf is False

    # Destructive action requiring confirmation
    allowed, conf, msg = guard.validate_action("system_shutdown", {})
    assert allowed is True
    assert conf is True

    # Dangerous project run command
    allowed, conf, msg = guard.validate_action("run_registered_project", {"run_command": "rmdir /s /q dist"})
    assert allowed is False
