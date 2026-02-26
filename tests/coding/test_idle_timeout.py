"""Tests for Fix 3: idle timeout (watchdog).

The watchdog thread terminates the claude process when no stdout output
arrives within idle_timeout seconds.

Note: test_watchdog_triggers_on_idle takes ~3s due to the real timeout wait.
"""

import json
import sys
import threading
import time
from unittest.mock import MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────


class _BlockingStdout:
    """Iterable that blocks until released — simulates a hanging process.

    When proc.terminate() fires its side_effect, it calls release.set(),
    unblocking __next__ which raises StopIteration to end the for-loop.
    """

    def __init__(self):
        self.release = threading.Event()

    def __iter__(self):
        return self

    def __next__(self):
        self.release.wait(timeout=30)  # safety: never hang forever in CI
        raise StopIteration


def _result_line(text="ok"):
    return json.dumps({
        "type": "result",
        "result": text,
        "session_id": "",
        "usage": {},
    }) + "\n"


# ── Tests ────────────────────────────────────────────────────────────────


def test_watchdog_triggers_on_idle(cc, tmp_assets_dir):
    """Process with no output is terminated after idle_timeout seconds."""
    stdout = _BlockingStdout()
    proc = MagicMock()
    proc.__enter__ = MagicMock(return_value=proc)
    proc.__exit__ = MagicMock(return_value=False)
    proc.stdout = stdout
    proc.stderr.read.return_value = ""
    proc.returncode = -15
    proc.wait.return_value = -15
    # terminate → unblock the hanging stdout so run_claude can finish
    proc.terminate.side_effect = lambda: stdout.release.set()

    with patch("subprocess.Popen", return_value=proc):
        t0 = time.monotonic()
        turn = cc.run_claude("test", idle_timeout=2)
        elapsed = time.monotonic() - t0

    assert "[超时]" in turn.result
    assert elapsed >= 2
    proc.terminate.assert_called()


def test_watchdog_no_trigger_on_active(cc, tmp_assets_dir):
    """Fast-completing process is NOT killed by the watchdog."""
    proc = MagicMock()
    proc.__enter__ = MagicMock(return_value=proc)
    proc.__exit__ = MagicMock(return_value=False)
    proc.stdout = iter([_result_line("done")])
    proc.stderr.read.return_value = ""
    proc.returncode = 0
    proc.wait.return_value = 0

    with patch("subprocess.Popen", return_value=proc):
        turn = cc.run_claude("test", idle_timeout=60)

    assert "[超时]" not in (turn.result or "")
    proc.terminate.assert_not_called()


def test_idle_timeout_default_value(cc, monkeypatch):
    """Default idle_timeout is 120 when --idle-timeout is not specified."""
    monkeypatch.setattr(sys, "argv", ["prog", "question"])
    _, _, _, idle_timeout, _ = cc.parse_args()
    assert idle_timeout == 120
