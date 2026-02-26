"""Shared session file utilities for coding-skill scripts.

Provides user-isolated session file paths and read/write helpers.
Used by both claude_chat.py and summarize_sessions.py to avoid duplication.
"""

import json
import re
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SESSION_FILE = ASSETS_DIR / "session.json"


def _safe_id(user_id: str) -> str:
    """将 user_id 转为安全的文件名片段（仅保留字母数字和下划线/连字符）。"""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', user_id)


def get_session_file(user_id: str | None = None) -> Path:
    """根据 user_id 返回对应的 session 文件路径。无 user_id 则返回全局文件（向后兼容）。"""
    if user_id:
        return ASSETS_DIR / f"session_{_safe_id(user_id)}.json"
    return SESSION_FILE


def load_sessions(user_id: str | None = None) -> dict:
    sf = get_session_file(user_id)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_sessions(sessions: dict, user_id: str | None = None) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    sf = get_session_file(user_id)
    sf.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
