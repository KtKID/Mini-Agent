"""Tests for Fix 2: stderr error feedback.

run_claude() now captures stderr (was DEVNULL) and reports errors / warnings.
All tests mock subprocess.Popen so no real claude CLI is needed.
"""

import json
from unittest.mock import MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_proc(stdout_lines=None, stderr_text="", returncode=0):
    """Create a mock Popen process with controllable stdout/stderr/returncode."""
    proc = MagicMock()
    proc.__enter__ = MagicMock(return_value=proc)
    proc.__exit__ = MagicMock(return_value=False)
    proc.stdout = iter(stdout_lines or [])
    proc.stderr.read.return_value = stderr_text
    proc.returncode = returncode
    proc.wait.return_value = returncode
    return proc


def _result_line(text="ok", session_id=""):
    """Build a single JSON result line as claude CLI would emit."""
    return json.dumps({
        "type": "result",
        "result": text,
        "session_id": session_id,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }) + "\n"


# ── Tests ────────────────────────────────────────────────────────────────


def test_normal_success(cc, tmp_assets_dir):
    """returncode=0, empty stderr → turn.result is the normal answer."""
    proc = _make_proc(
        stdout_lines=[_result_line("answer text")],
        stderr_text="",
        returncode=0,
    )
    with patch("subprocess.Popen", return_value=proc):
        turn = cc.run_claude("test", idle_timeout=300)

    assert turn.result == "answer text"
    assert "[错误]" not in turn.result


def test_nonzero_exit_captures_stderr(cc, tmp_assets_dir):
    """returncode≠0 with stderr → error message in turn.result."""
    proc = _make_proc(
        stdout_lines=[],
        stderr_text="Error: authentication failed\n",
        returncode=1,
    )
    with patch("subprocess.Popen", return_value=proc):
        turn = cc.run_claude("test", idle_timeout=300)

    assert "[错误]" in turn.result
    assert "authentication failed" in turn.result


def test_nonzero_exit_no_stderr(cc, tmp_assets_dir):
    """returncode≠0, empty stderr → error message mentions '无 stderr'."""
    proc = _make_proc(stdout_lines=[], stderr_text="", returncode=2)
    with patch("subprocess.Popen", return_value=proc):
        turn = cc.run_claude("test", idle_timeout=300)

    assert "[错误]" in turn.result
    assert "无 stderr 输出" in turn.result


def test_warning_on_success_with_stderr(cc, tmp_assets_dir, capsys):
    """returncode=0 but has stderr → warning printed, result NOT overwritten."""
    proc = _make_proc(
        stdout_lines=[_result_line("good answer")],
        stderr_text="deprecation warning: xyz\n",
        returncode=0,
    )
    with patch("subprocess.Popen", return_value=proc):
        turn = cc.run_claude("test", idle_timeout=300)

    assert turn.result == "good answer"
    assert "[错误]" not in turn.result
    captured = capsys.readouterr().out
    assert "stderr" in captured
