"""
IRIS Project Runner Subsystem
Executes approved developer project scripts safely, opens projects in IDEs,
monitors background process health, and tracks real execution status.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional
import psutil

from ..core.logger import get_logger
from ..database.project_registry import ProjectRegistry, ProjectInfo
from .security import SecurityGuard

logger = get_logger("project_runner")


class ProjectRunner:
    """Executes registered project run commands and handles IDE launch."""

    def __init__(self):
        self.registry = ProjectRegistry()
        self.security = SecurityGuard()
        self.active_processes = {}

    def run_project(self, project_name_or_query: str) -> Tuple[bool, str, Optional[ProjectInfo]]:
        """
        Resolves project from registry, validates run command security,
        and launches the project process.
        """
        project: Optional[ProjectInfo] = self.registry.find_project(project_name_or_query)
        if not project:
            return False, f"Project '{project_name_or_query}' registry mein nahi mila. Please check name.", None

        proj_path = Path(project.path)
        if not proj_path.exists():
            return False, f"Project path exist nahi karta: {project.path}", project

        run_cmd = project.run_command
        if not run_cmd:
            return False, f"Project '{project.name}' ke liye koi approved run command set nahi hai.", project

        # Validate security
        is_safe, reason = self.security.validate_command_string(run_cmd)
        if not is_safe:
            return False, f"Security Warning: Run command blocked - {reason}", project

        logger.info(f"Running project '{project.name}' via command: '{run_cmd}' in {proj_path}")

        try:
            # Spawn in a separate process group in project directory
            proc = subprocess.Popen(
                run_cmd,
                cwd=str(proj_path),
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0
            )

            # Brief health check (wait 0.8s)
            time.sleep(0.8)
            poll_code = proc.poll()
            if poll_code is not None and poll_code != 0:
                return False, f"Project exited unexpectedly with code {poll_code}", project

            self.active_processes[project.name] = proc
            self.registry.update_last_opened(project.name)

            return True, f"Project '{project.name}' ({project.tech_stack}) successfully start ho gaya hai (PID {proc.pid}).", project

        except Exception as e:
            logger.error(f"Failed to run project {project.name}: {e}")
            return False, f"Execution failed: {str(e)}", project

    def open_project_in_editor(self, query: str = "", recent: bool = False) -> Tuple[bool, str, Optional[ProjectInfo]]:
        """Opens project directory in Visual Studio Code or Explorer."""
        if recent:
            project = self.registry.get_most_recent_project()
        else:
            project = self.registry.find_project(query)

        if not project:
            return False, "Koi project nahi mila.", None

        proj_path = Path(project.path)
        if not proj_path.exists():
            return False, f"Path exist nahi karta: {project.path}", project

        logger.info(f"Opening project '{project.name}' at {proj_path} in VS Code")

        # Open in VS Code if available, else Explorer
        try:
            subprocess.Popen(["cmd.exe", "/c", "code", str(proj_path)], shell=False)
            self.registry.update_last_opened(project.name)
            return True, f"Project '{project.name}' VS Code mein open kar diya hai.", project
        except Exception:
            try:
                subprocess.Popen(["explorer.exe", str(proj_path)], shell=False)
                return True, f"Project '{project.name}' Explorer mein open kar diya hai.", project
            except Exception as e2:
                return False, f"Error opening project: {e2}", project
