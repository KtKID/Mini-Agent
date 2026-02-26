"""Shared fixtures for coding-skill tests."""

import importlib.util
from pathlib import Path

import pytest

# ── 通过 importlib 加载 claude_chat（目录名 coding-skill 含连字符，无法常规 import）──
_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "mini_agent" / "skills" / "coding-skill" / "scripts" / "claude_chat.py"
)
_spec = importlib.util.spec_from_file_location("claude_chat", _SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.fixture
def cc():
    """Return the claude_chat module."""
    return _module


@pytest.fixture
def tmp_assets_dir(monkeypatch, tmp_path):
    """Redirect ASSETS_DIR and SESSION_FILE to a temp directory.

    All session file I/O within the test is isolated to tmp_path.
    monkeypatch automatically restores originals after each test.
    """
    monkeypatch.setattr(_module, "ASSETS_DIR", tmp_path)
    monkeypatch.setattr(_module, "SESSION_FILE", tmp_path / "session.json")
    yield tmp_path
