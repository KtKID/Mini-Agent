"""Shared fixtures for coding-skill tests."""

import importlib.util
import sys
from pathlib import Path

import pytest

# ── 将 scripts 目录加入 sys.path，使 session_utils 可被 import ──────────────
_SCRIPTS_DIR = str(
    Path(__file__).resolve().parent.parent.parent
    / "mini_agent" / "skills" / "coding-skill" / "scripts"
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# ── 通过 importlib 加载 claude_chat（目录名 coding-skill 含连字符，无法常规 import）──
_SCRIPT_PATH = Path(_SCRIPTS_DIR) / "claude_chat.py"
_spec = importlib.util.spec_from_file_location("claude_chat", _SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

# session_utils 已被 claude_chat 导入，可直接 import
import session_utils as _session_utils


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
    # Patch session_utils（函数内部读取的模块全局变量）
    monkeypatch.setattr(_session_utils, "ASSETS_DIR", tmp_path)
    monkeypatch.setattr(_session_utils, "SESSION_FILE", tmp_path / "session.json")
    # Patch claude_chat 的导入绑定（测试中直接访问 cc.SESSION_FILE 时需要）
    monkeypatch.setattr(_module, "ASSETS_DIR", tmp_path)
    monkeypatch.setattr(_module, "SESSION_FILE", tmp_path / "session.json")
    yield tmp_path
