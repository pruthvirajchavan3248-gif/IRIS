"""
IRIS Project Registry Module
Manages developer coding projects, detects tech stacks, and resolves voice project queries.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import difflib

from .db import get_db
from ..core.logger import get_logger

logger = get_logger("project_registry")


@dataclass
class ProjectInfo:
    id: Optional[int]
    name: str
    path: str
    tech_stack: str
    run_command: str
    test_command: str = ""
    build_command: str = ""
    last_opened: Optional[str] = None
    created_at: Optional[str] = None
    notes: str = ""


class ProjectRegistry:
    """Manages project registrations, auto-discovery of technologies, and recent project resolution."""

    def __init__(self):
        self.db = get_db()

    @staticmethod
    def detect_tech_stack(project_dir: Path) -> str:
        """Inspects folder indicators to determine language and framework."""
        if not project_dir.exists() or not project_dir.is_dir():
            return "Generic"

        files = [f.name.lower() for f in project_dir.iterdir() if f.is_file()]
        dirs = [d.name.lower() for d in project_dir.iterdir() if d.is_dir()]

        # Rust
        if "cargo.toml" in files:
            return "Rust (Cargo)"
        
        # Node / JavaScript / TypeScript
        if "package.json" in files:
            try:
                pkg_text = (project_dir / "package.json").read_text(encoding="utf-8", errors="ignore").lower()
                if "next" in pkg_text:
                    return "Next.js (Node.js)"
                if "react" in pkg_text:
                    return "React (Node.js)"
                if "vue" in pkg_text:
                    return "Vue (Node.js)"
                if "electron" in pkg_text:
                    return "Electron (Node.js)"
                return "Node.js"
            except Exception:
                return "Node.js"

        # Python
        if any(f in files for f in ["pyproject.toml", "requirements.txt", "setup.py", "pipfile", "main.py"]):
            return "Python"

        # Go
        if "go.mod" in files:
            return "Go"

        # Java / Kotlin
        if "pom.xml" in files or "build.gradle" in files or "build.gradle.kts" in files:
            return "Java / Kotlin"

        # C++ / C / CMake
        if "cmakelists.txt" in files or "makefile" in files:
            return "C/C++"

        # Flutter / Dart
        if "pubspec.yaml" in files:
            return "Flutter / Dart"

        return "Generic"

    @staticmethod
    def suggest_default_run_command(tech_stack: str, project_dir: Path) -> str:
        """Proposes a safe standard run command according to tech stack."""
        tech = tech_stack.lower()
        if "rust" in tech:
            return "cargo run"
        if "next" in tech:
            return "npm run dev"
        if "react" in tech or "vue" in tech or "node" in tech:
            return "npm start"
        if "python" in tech:
            if (project_dir / "main.py").exists():
                return "python main.py"
            if (project_dir / "app.py").exists():
                return "python app.py"
            return "python -m run"
        if "go" in tech:
            return "go run ."
        if "flutter" in tech:
            return "flutter run"
        return "code ."

    def register_project(self, name: str, path_str: str, run_command: Optional[str] = None, notes: str = "") -> ProjectInfo:
        """Registers a new project or updates existing one."""
        p = Path(path_str).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Project directory does not exist: {path_str}")

        tech = self.detect_tech_stack(p)
        cmd = run_command or self.suggest_default_run_command(tech, p)

        conn = self.db._get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO registered_projects (name, path, tech_stack, run_command, notes, last_opened)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    path=excluded.path,
                    tech_stack=excluded.tech_stack,
                    run_command=excluded.run_command,
                    notes=excluded.notes
                """,
                (name, str(p), tech, cmd, notes)
            )

        logger.info(f"Registered project '{name}' ({tech}) at {p}")
        return self.get_project_by_name(name)

    def get_all_projects(self) -> List[ProjectInfo]:
        conn = self.db._get_connection()
        cur = conn.execute("SELECT * FROM registered_projects ORDER BY name ASC")
        results = []
        for row in cur.fetchall():
            results.append(ProjectInfo(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                tech_stack=row["tech_stack"],
                run_command=row["run_command"],
                test_command=row["test_command"] or "",
                build_command=row["build_command"] or "",
                last_opened=row["last_opened"],
                created_at=row["created_at"],
                notes=row["notes"] or ""
            ))
        return results

    def get_project_by_name(self, name: str) -> Optional[ProjectInfo]:
        conn = self.db._get_connection()
        cur = conn.execute("SELECT * FROM registered_projects WHERE LOWER(name) = LOWER(?)", (name,))
        row = cur.fetchone()
        if not row:
            return None
        return ProjectInfo(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            tech_stack=row["tech_stack"],
            run_command=row["run_command"],
            test_command=row["test_command"] or "",
            build_command=row["build_command"] or "",
            last_opened=row["last_opened"],
            created_at=row["created_at"],
            notes=row["notes"] or ""
        )

    def find_project(self, query: str) -> Optional[ProjectInfo]:
        """Fuzzy/clean search for a project by spoken name (e.g. 'Level Up', 'levelup')."""
        clean_query = query.strip().lower()
        projects = self.get_all_projects()
        if not projects:
            return None

        # 1. Exact match
        for p in projects:
            if clean_query == p.name.lower():
                return p

        # 2. Simplified match (no spaces, punctuation)
        simple_q = "".join(c for c in clean_query if c.isalnum())
        for p in projects:
            simple_name = "".join(c for c in p.name.lower() if c.isalnum())
            if simple_q and (simple_q == simple_name or simple_q in simple_name or simple_name in simple_q):
                return p

        # 3. Difflib fuzzy match
        names = [p.name.lower() for p in projects]
        matches = difflib.get_close_matches(clean_query, names, n=1, cutoff=0.6)
        if matches:
            matched_name = matches[0]
            for p in projects:
                if p.name.lower() == matched_name:
                    return p

        return None

    def get_most_recent_project(self) -> Optional[ProjectInfo]:
        """Finds the most recently modified or opened project on disk or in DB."""
        projects = self.get_all_projects()
        if not projects:
            return None

        # Sort projects by directory modification time on filesystem
        def get_mtime(proj: ProjectInfo) -> float:
            try:
                p = Path(proj.path)
                if p.exists():
                    return p.stat().st_mtime
            except Exception:
                pass
            return 0.0

        projects_sorted = sorted(projects, key=get_mtime, reverse=True)
        if projects_sorted and get_mtime(projects_sorted[0]) > 0:
            return projects_sorted[0]

        # Fallback to database last_opened or created_at
        conn = self.db._get_connection()
        cur = conn.execute("SELECT * FROM registered_projects ORDER BY datetime(COALESCE(last_opened, created_at)) DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            return ProjectInfo(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                tech_stack=row["tech_stack"],
                run_command=row["run_command"],
                last_opened=row["last_opened"],
                created_at=row["created_at"],
                notes=row["notes"] or ""
            )
        return None

    def update_last_opened(self, project_name: str) -> None:
        conn = self.db._get_connection()
        with conn:
            conn.execute(
                "UPDATE registered_projects SET last_opened = CURRENT_TIMESTAMP WHERE LOWER(name) = LOWER(?)",
                (project_name,)
            )

    def delete_project(self, project_id: int) -> bool:
        conn = self.db._get_connection()
        with conn:
            cur = conn.execute("DELETE FROM registered_projects WHERE id = ?", (project_id,))
            return cur.rowcount > 0
