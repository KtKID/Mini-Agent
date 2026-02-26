"""Tests for claude_chat.parse_args() — covers --user, --idle-timeout, --new, --resume."""

import sys


def test_parse_simple_prompt(cc, monkeypatch):
    """Simple prompt, all other flags default."""
    monkeypatch.setattr(sys, "argv", ["prog", "hello world"])
    resume_id, prompt, force_new, idle_timeout, user_id = cc.parse_args()
    assert prompt == "hello world"
    assert resume_id is None
    assert force_new is False
    assert idle_timeout == 120
    assert user_id is None


def test_parse_new_flag(cc, monkeypatch):
    """--new sets force_new=True."""
    monkeypatch.setattr(sys, "argv", ["prog", "--new", "question"])
    _, prompt, force_new, _, _ = cc.parse_args()
    assert force_new is True
    assert prompt == "question"


def test_parse_resume_with_id(cc, monkeypatch):
    """--resume <id> captures the session id."""
    monkeypatch.setattr(sys, "argv", ["prog", "--resume", "abc123", "question"])
    resume_id, prompt, _, _, _ = cc.parse_args()
    assert resume_id == "abc123"
    assert prompt == "question"


def test_parse_user_flag(cc, monkeypatch):
    """--user <id> captures user identifier (Fix 1)."""
    monkeypatch.setattr(sys, "argv", ["prog", "--user", "ou_xxxx", "question"])
    _, prompt, _, _, user_id = cc.parse_args()
    assert user_id == "ou_xxxx"
    assert prompt == "question"


def test_parse_idle_timeout(cc, monkeypatch):
    """--idle-timeout <n> overrides default 120s (Fix 3)."""
    monkeypatch.setattr(sys, "argv", ["prog", "--idle-timeout", "300", "question"])
    _, prompt, _, idle_timeout, _ = cc.parse_args()
    assert idle_timeout == 300
    assert prompt == "question"


def test_parse_all_combined(cc, monkeypatch):
    """All flags together parse correctly."""
    monkeypatch.setattr(sys, "argv", [
        "prog", "--user", "u1", "--idle-timeout", "60", "--new", "complex question",
    ])
    resume_id, prompt, force_new, idle_timeout, user_id = cc.parse_args()
    assert user_id == "u1"
    assert idle_timeout == 60
    assert force_new is True
    assert prompt == "complex question"
    assert resume_id is None
