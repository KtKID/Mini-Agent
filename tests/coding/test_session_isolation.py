"""Tests for Fix 1: session.json user isolation.

Covers: _safe_id, get_session_file, load/save/update_session with user_id,
        get_latest_session per user, handle_command /sessions per user.
"""


# ── A. Pure function tests (no temp dir needed) ─────────────────────────


class TestSafeId:
    """_safe_id sanitises user identifiers for safe file names."""

    def test_alphanumeric(self, cc):
        assert cc._safe_id("abc123") == "abc123"

    def test_special_chars(self, cc):
        assert cc._safe_id("ou_xxx@feishu.cn") == "ou_xxx_feishu_cn"

    def test_preserves_hyphen_and_underscore(self, cc):
        assert cc._safe_id("user-01_test") == "user-01_test"


class TestGetSessionFile:
    """get_session_file returns the right Path for each user_id."""

    def test_no_user_returns_global(self, cc):
        assert cc.get_session_file(None) == cc.SESSION_FILE

    def test_with_user_returns_per_user(self, cc):
        result = cc.get_session_file("alice")
        assert result.name == "session_alice.json"


# ── B. File isolation tests (use tmp_assets_dir fixture) ─────────────────


def test_save_load_global_session(cc, tmp_assets_dir):
    """No user_id → read/write session.json (backward compat)."""
    data = {"sid1": {"first_prompt": "hello", "updated_at": "2026-01-01T00:00:00"}}
    cc.save_sessions(data)
    loaded = cc.load_sessions()
    assert loaded == data
    assert (tmp_assets_dir / "session.json").exists()


def test_save_load_user_session(cc, tmp_assets_dir):
    """user_id='u1' → read/write session_u1.json."""
    data = {"sid1": {"first_prompt": "hello", "updated_at": "2026-01-01T00:00:00"}}
    cc.save_sessions(data, user_id="u1")
    loaded = cc.load_sessions(user_id="u1")
    assert loaded == data
    assert (tmp_assets_dir / "session_u1.json").exists()


def test_two_users_isolated(cc, tmp_assets_dir):
    """User A's data is invisible to user B and vice versa."""
    cc.save_sessions({"s_a": {"first_prompt": "A"}}, user_id="A")
    cc.save_sessions({"s_b": {"first_prompt": "B"}}, user_id="B")

    a_data = cc.load_sessions(user_id="A")
    b_data = cc.load_sessions(user_id="B")

    assert "s_a" in a_data and "s_b" not in a_data
    assert "s_b" in b_data and "s_a" not in b_data


def test_update_session_creates_new_entry(cc, tmp_assets_dir):
    """First update_session creates a new entry with correct fields."""
    cc.update_session("sid1", "hello", "world",
                      input_tokens=10, output_tokens=20, user_id="u1")
    sessions = cc.load_sessions(user_id="u1")
    assert "sid1" in sessions
    entry = sessions["sid1"]
    assert entry["first_prompt"] == "hello"
    assert entry["turns"] == 1
    assert entry["total_tokens"] == 30


def test_update_session_increments_turns(cc, tmp_assets_dir):
    """Subsequent updates increment turns and refresh last_prompt."""
    cc.update_session("sid1", "q1", "a1", user_id="u1")
    cc.update_session("sid1", "q2", "a2", user_id="u1")
    sessions = cc.load_sessions(user_id="u1")
    assert sessions["sid1"]["turns"] == 2
    assert sessions["sid1"]["last_prompt"] == "q2"


def test_get_latest_session_per_user(cc, tmp_assets_dir):
    """get_latest_session returns the most-recently-updated session for the given user."""
    cc.save_sessions({
        "old_sid": {"updated_at": "2026-01-01T00:00:00"},
        "new_sid": {"updated_at": "2026-01-02T00:00:00"},
    }, user_id="A")
    assert cc.get_latest_session(user_id="A") == "new_sid"


def test_no_user_fallback_global(cc, tmp_assets_dir):
    """Global session.json is separate from per-user files."""
    cc.save_sessions({"global_sid": {"updated_at": "2026-01-01"}})
    assert "global_sid" in cc.load_sessions(None)
    assert cc.load_sessions(user_id="A") == {}


# ── C. handle_command tests ──────────────────────────────────────────────


def test_handle_sessions_uses_user_id(cc, tmp_assets_dir, capsys):
    """/sessions for user A shows A's data; user B sees nothing."""
    cc.save_sessions({"sid_a": {
        "summary": "A's session",
        "last_reply_snippet": "",
        "turns": 2,
        "updated_at": "2026-01-01",
    }}, user_id="A")

    cc.handle_command("/sessions", None, user_id="A")
    out_a = capsys.readouterr().out
    assert "1 个" in out_a

    cc.handle_command("/sessions", None, user_id="B")
    out_b = capsys.readouterr().out
    assert "暂无" in out_b


# ── D. Edge / boundary cases ────────────────────────────────────────────


def test_safe_id_empty_string(cc):
    """Empty string → remains empty (edge case)."""
    assert cc._safe_id("") == ""


def test_safe_id_all_special(cc):
    """All-special-char input → all replaced with underscores."""
    assert cc._safe_id("@#$%") == "____"


def test_load_sessions_corrupt_file(cc, tmp_assets_dir):
    """Corrupt (non-JSON) session file → returns empty dict."""
    (tmp_assets_dir / "session.json").write_text("not json!!!", encoding="utf-8")
    assert cc.load_sessions() == {}


def test_update_session_long_result_truncated(cc, tmp_assets_dir):
    """Result > 200 chars → last_reply_snippet truncated to 200."""
    long_result = "x" * 1000
    cc.update_session("sid1", "q", long_result, user_id="u1")
    sessions = cc.load_sessions(user_id="u1")
    assert len(sessions["sid1"]["last_reply_snippet"]) == 200
