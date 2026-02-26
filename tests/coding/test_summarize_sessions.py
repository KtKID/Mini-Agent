"""summarize_sessions.py 会话摘要生成测试。

测试覆盖：
  - summarize_one（成功返回、超时降级情况、信息为空的情况）
  - process_sessions（跳过有摘要的条目、强制全部更新、指定 target_id）
"""

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ── Load the module (same importlib trick as conftest) ───────────────────

_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "mini_agent" / "skills" / "coding-skill" / "scripts" / "summarize_sessions.py"
)
_spec = importlib.util.spec_from_file_location("summarize_sessions", _SCRIPT_PATH)
_ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ss)


@pytest.fixture
def ss():
    """返回总结运行脚本 summarize_sessions 模块"""
    return _ss


@pytest.fixture
def tmp_ss_assets(monkeypatch, tmp_path):
    """重定向 summarize_sessions 里的文件路径目录到临时文件夹。"""
    monkeypatch.setattr(_ss, "ASSETS_DIR", tmp_path)
    monkeypatch.setattr(_ss, "SESSION_FILE", tmp_path / "session.json")
    yield tmp_path


# ── summarize_one tests ─────────────────────────────────────────────────


def test_summarize_one_success(ss):
    """
    测试说明：当 claude CLI 正常返回一个有效的摘要时，则应直接采纳该摘要（截断最大100字符）。
    模拟数据：
      - info 内容：第一条要求写函数，最终回复已添加。
      - claude CLI stdout："编写并完善 Python 函数，添加类型注解"
    预期结果：返回的摘要就是 "编写并完善 Python 函数，添加类型注解"。
    """
    info = {
        "first_prompt": "帮我写个函数",
        "last_prompt": "加上类型注解",
        "last_reply_snippet": "好的，已添加",
        "turns": 3,
    }
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "编写并完善 Python 函数，添加类型注解"

    with patch("subprocess.run", return_value=mock_result):
        summary = ss.summarize_one("sid1", info)

    assert summary == "编写并完善 Python 函数，添加类型注解"


def test_summarize_one_fallback_on_timeout(ss):
    """
    测试说明：当获取大模型分析超时或系统故障，代码要执行降级操作。
    模拟数据：
      - first_prompt 是一个非常长的语句（超过 50 字符）
      - subprocess 系统调用异常 TimeoutError
    预期结果：不会崩溃并能返回前 50 个字节作为应急的会话摘要总结。
    """
    info = {"first_prompt": "这是一个很长的问题" * 10, "last_prompt": "", "last_reply_snippet": "", "turns": 1}

    with patch("subprocess.run", side_effect=TimeoutError):
        summary = ss.summarize_one("sid1", info)

    assert len(summary) <= 50
    assert summary == info["first_prompt"][:50]


def test_summarize_one_no_prompt(ss):
    """
    测试说明：测试完全异常/空的传入 info，无有效 prompt 是否会正常处理。
    模拟数据：
      - 空的各种入参 prompt/turns。
      - claude 命令行没有找到（FileNotFoundError）
    预期结果：捕获到错误并降级输出固定标识 "(无摘要)"。
    """
    info = {"first_prompt": "", "last_prompt": "", "last_reply_snippet": "", "turns": 0}

    with patch("subprocess.run", side_effect=FileNotFoundError):
        summary = ss.summarize_one("sid1", info)

    assert summary == "(无摘要)"


# ── process_sessions tests ──────────────────────────────────────────────


def test_process_sessions_skips_with_summary(ss):
    """
    测试说明：验证默认遍历且文件内已有 summary 字段时的条目该做跳过处理。
    模拟数据：
      - options：do_all=False
      - session：sid1 包含 summary "existing summary"
    预期结果：总结计数器为 0，因为旧有未更新项目直接被略过，并且核心逻辑 summarize_one 也不会被调用。
    """
    sessions = {
        "sid1": {"summary": "existing summary", "first_prompt": "q"},
    }
    with patch.object(ss, "summarize_one") as mock_summarize:
        updated = ss.process_sessions(sessions, target_id=None, do_all=False)

    assert updated == 0
    mock_summarize.assert_not_called()


def test_process_sessions_forces_all(ss):
    """
    测试说明：验证 do_all 参数为 True 的强制重制工作模式的有效性。
    模拟数据：
      - options：do_all=True
      - mock 调用固定返回：'new summary'
    预期结果：无论老数据是否有摘要，都会被强制调用并应用新生成总结数据。
    """
    sessions = {
        "sid1": {"summary": "old", "first_prompt": "q"},
    }
    with patch.object(ss, "summarize_one", return_value="new summary"):
        updated = ss.process_sessions(sessions, target_id=None, do_all=True)

    assert updated == 1
    assert sessions["sid1"]["summary"] == "new summary"


def test_process_sessions_target_id(ss):
    """
    测试说明：验证通过 `--session <sid>` 精准备选指定的 session 更新机制。
    模拟数据：列表中包含 sid1, sid2。目标指定只需要 sid1
    预期结果：只有目标 ID 获得了摘要，计数为 1。未包含选定的对象会保持原本不动。
    """
    sessions = {
        "sid1": {"first_prompt": "q1"},
        "sid2": {"first_prompt": "q2"},
    }
    with patch.object(ss, "summarize_one", return_value="summary") as mock:
        updated = ss.process_sessions(sessions, target_id="sid1", do_all=False)

    assert updated == 1
    assert sessions["sid1"]["summary"] == "summary"
    assert "summary" not in sessions.get("sid2", {})
