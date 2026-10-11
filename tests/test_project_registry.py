"""
Unit Tests for Developer Project Registry & Auto-Detection
"""

import tempfile
import pytest
from pathlib import Path
from iris.database.project_registry import ProjectRegistry
from iris.database.db import DatabaseManager


@pytest.fixture
def clean_registry():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    DatabaseManager._instance = None
    DatabaseManager(db_path=db_path)
    reg = ProjectRegistry()
    yield reg

    reg.db.close()
    DatabaseManager._instance = None
    try:
        db_path.unlink(missing_ok=True)
    except Exception:
        pass



def test_tech_stack_detection(tmp_path):
    # Python project
    py_proj = tmp_path / "py_app"
    py_proj.mkdir()
    (py_proj / "requirements.txt").write_text("requests==2.31.0")
    (py_proj / "main.py").write_text("print('hello')")
    assert ProjectRegistry.detect_tech_stack(py_proj) == "Python"
    assert ProjectRegistry.suggest_default_run_command("Python", py_proj) == "python main.py"

    # Rust project
    rs_proj = tmp_path / "rust_app"
    rs_proj.mkdir()
    (rs_proj / "Cargo.toml").write_text("[package]\nname = 'test'")
    assert ProjectRegistry.detect_tech_stack(rs_proj) == "Rust (Cargo)"
    assert ProjectRegistry.suggest_default_run_command("Rust (Cargo)", rs_proj) == "cargo run"

    # Node.js project
    node_proj = tmp_path / "node_app"
    node_proj.mkdir()
    (node_proj / "package.json").write_text('{"name": "test-app"}')
    assert "Node.js" in ProjectRegistry.detect_tech_stack(node_proj)


def test_project_registration_and_search(clean_registry, tmp_path):
    proj_dir = tmp_path / "LevelUp"
    proj_dir.mkdir()
    (proj_dir / "main.py").write_text("print('Level Up!')")

    # Register
    clean_registry.register_project("Level Up", str(proj_dir), run_command="python main.py")

    # Exact search
    exact = clean_registry.find_project("Level Up")
    assert exact is not None
    assert exact.name == "Level Up"
    assert exact.run_command == "python main.py"

    # Fuzzy / spoken search ("levelup")
    fuzzy = clean_registry.find_project("levelup")
    assert fuzzy is not None
    assert fuzzy.name == "Level Up"


def test_most_recent_project_resolution(clean_registry, tmp_path):
    p1 = tmp_path / "OldProject"
    p1.mkdir()
    clean_registry.register_project("OldProject", str(p1))

    p2 = tmp_path / "NewProject"
    p2.mkdir()
    clean_registry.register_project("NewProject", str(p2))

    # Mark NewProject as recently opened
    clean_registry.update_last_opened("NewProject")

    recent = clean_registry.get_most_recent_project()
    assert recent is not None
    assert recent.name == "NewProject"
