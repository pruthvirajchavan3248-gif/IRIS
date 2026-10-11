"""
IRIS Security Guard & Action Validator
Enforces execution safety, prevents malicious or destructive shell executions,
and manages confirmation protocols for high-risk actions.
"""

import re
import shlex
from typing import Dict, Any, Tuple, Optional
from ..core.config import get_config
from ..core.logger import get_logger

logger = get_logger("security")


class SecurityGuard:
    """Validates actions and scripts prior to execution."""

    # Prohibited dangerous shell patterns
    DANGEROUS_PATTERNS = [
        r"\bformat\s+[a-z]:",
        r"\brmdir\s+/[sS]",
        r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]",
        r"\bdiskpart\b",
        r"\breg\s+(delete|add)\b",
        r"\bvssadmin\s+delete\b",
        r"\bbcdedit\b",
        r"\bpowershell\s+-(enc|encodedcommand)\b",
        r"\bcurl\s+.+?\|\s*(sh|powershell|cmd)",
        r"\bwget\s+.+?\|\s*(sh|powershell|cmd)",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # Fork bomb
    ]

    # Actions that require explicit user voice confirmation
    CONFIRMATION_REQUIRED_ACTIONS = [
        "system_shutdown",
        "system_restart",
        "delete_file",
        "clear_database_memory",
        "terminate_all_processes",
    ]

    def __init__(self):
        self.config = get_config()
        self._compiled_regexes = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS]

    def validate_command_string(self, cmd_str: str) -> Tuple[bool, str]:
        """
        Scans a shell command line string for unsafe patterns.
        Returns:
            (is_safe, reason)
        """
        if not cmd_str or not cmd_str.strip():
            return False, "Command is empty"

        cleaned = cmd_str.strip()

        for pattern in self._compiled_regexes:
            if pattern.search(cleaned):
                logger.critical(f"Security Alert: Blocked dangerous command pattern in: '{cleaned}'")
                return False, f"Command matched dangerous execution pattern: {pattern.pattern}"

        return True, "Safe"

    def validate_action(self, action_type: str, parameters: Dict[str, Any]) -> Tuple[bool, bool, str]:
        """
        Validates an action dictionary.
        Returns:
            (is_allowed, requires_confirmation, message)
        """
        # 1. Check if action requires confirmation
        requires_conf = action_type in self.CONFIRMATION_REQUIRED_ACTIONS

        # 2. Check for shell execution payloads
        if action_type in ["run_shell_command", "run_script"]:
            cmd = parameters.get("command", "")
            is_safe, reason = self.validate_command_string(cmd)
            if not is_safe:
                return False, False, f"Execution blocked by IRIS Security Guard: {reason}"
            if self.config.require_confirmation_for_destructive:
                requires_conf = True

        # 3. Check for project run commands
        if action_type == "run_registered_project":
            cmd = parameters.get("run_command", "")
            if cmd:
                is_safe, reason = self.validate_command_string(cmd)
                if not is_safe:
                    return False, False, f"Project run command blocked: {reason}"

        return True, requires_conf, "Validated"

    @staticmethod
    def sanitize_arguments(args: list) -> list:
        """Sanitizes process argument list."""
        return [str(a).strip() for a in args if str(a).strip()]
