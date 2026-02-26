"""run_claude() 函数的会话持久化和命令构建测试。

验证 run_claude() 是否正确执行了以下功能：
  - 成功调用后持久化保存会话数据
  - 持久化时使用累积的 token 计算值
  - 尊重并使用指定的 user_id 以实现文件隔离
  - 构建正确的带有/不带有 --resume 参数的子进程执行命令
"""

import json
from unittest.mock import MagicMock, patch, call


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_proc(stdout_lines=None, stderr_text="", returncode=0):
    """创建并返回配置好 stdout/stderr/returncode 的 Popen mock 对象。"""
    proc = MagicMock()
    proc.__enter__ = MagicMock(return_value=proc)
    proc.__exit__ = MagicMock(return_value=False)
    proc.stdout = iter(stdout_lines or [])
    proc.stderr.read.return_value = stderr_text
    proc.returncode = returncode
    proc.wait.return_value = returncode
    return proc


def _result_line(text="ok", session_id="test-sid",
                 input_tokens=10, output_tokens=5):
    """构建一行模拟结果 JSON 文本。"""
    return json.dumps({
        "type": "result",
        "result": text,
        "session_id": session_id,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }) + "\n"


def _message_delta_line(input_tokens=100, output_tokens=50):
    """构建一行模拟消息增量 JSON 文本（用于累积 token 测试）。"""
    return json.dumps({
        "type": "stream_event",
        "event": {
            "type": "message_delta",
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        },
    }) + "\n"


# ── Tests ────────────────────────────────────────────────────────────────


def test_session_saved_on_success(cc, tmp_assets_dir):
    """
    测试说明：当调用 run_claude() 成功并获取到结果时，应验证新对话被保存到文件中。
    模拟数据：
      - prompt 提问 = "hello"
      - stdin 模拟输出 = 正常的结果 ("answer", "sid-001")
    预期结果：读取的 session 文件中包含了 "sid-001"，且轮次 turns 为 1。
    """
    proc = _make_proc(stdout_lines=[_result_line("answer", "sid-001")])
    with patch("subprocess.Popen", return_value=proc):
        cc.run_claude("hello", idle_timeout=300)

    sessions = cc.load_sessions()
    assert "sid-001" in sessions
    entry = sessions["sid-001"]
    assert entry["first_prompt"] == "hello"
    assert entry["turns"] == 1


def test_session_tokens_from_cumulative(cc, tmp_assets_dir):
    """
    测试说明：测试会话持久化时使用的 tokens 是否优先使用累积值，而非最后一个结果对象中的值。
    模拟数据：
      - stream_event 中的 message_delta token = (200 in, 100 out)
      - result 对象中的 token = (10 in, 5 out)
    预期结果：最终保存在 json 的 total_tokens 应当是累加计算得出的 300，而不是 result 指定的 15。
    """
    proc = _make_proc(stdout_lines=[
        _message_delta_line(200, 100),
        _result_line("answer", "sid-002", input_tokens=10, output_tokens=5),
    ])
    with patch("subprocess.Popen", return_value=proc):
        cc.run_claude("test", idle_timeout=300)

    sessions = cc.load_sessions()
    entry = sessions["sid-002"]
    # 累加优先于最后返回的 usage（200 + 100 = 300）
    assert entry["total_tokens"] == 300


def test_session_saved_with_user_id(cc, tmp_assets_dir):
    """
    测试说明：验证带有 user_id 参数时，是否只存储到对应用户的特定文件中，而不污染全局配置。
    模拟数据：
      - user_id = "u1"
      - result session_id = "sid-003"
    预期结果：
      - 全局（无 user_id）加载得到 {} 
      - 通过 user_id="u1" 加载能正常读取到 "sid-003"。
    """
    proc = _make_proc(stdout_lines=[_result_line("ans", "sid-003")])
    with patch("subprocess.Popen", return_value=proc):
        cc.run_claude("test", idle_timeout=300, user_id="u1")

    # 全局文件应当不含最新测试生成的数据
    assert cc.load_sessions() == {}
    # 属于特定的 user 文件里应当含有
    sessions = cc.load_sessions(user_id="u1")
    assert "sid-003" in sessions


def test_cmd_includes_resume_flag(cc, tmp_assets_dir):
    """
    测试说明：确保向子进程传输了正确的恢复命令参数 `--resume`。
    模拟数据：传入 session_id = "resume-id"
    预期结果：拼装给 Popen 执行的 cmd 数组中包含 "--resume" 及其参数 "resume-id"。
    """
    proc = _make_proc(stdout_lines=[_result_line()])
    with patch("subprocess.Popen", return_value=proc) as mock_popen:
        cc.run_claude("test", session_id="resume-id", idle_timeout=300)

    cmd = mock_popen.call_args[0][0]
    assert "--resume" in cmd
    resume_idx = cmd.index("--resume")
    assert cmd[resume_idx + 1] == "resume-id"


def test_cmd_excludes_resume_when_none(cc, tmp_assets_dir):
    """
    测试说明：当新开启一次对话（传入 session_id=None 时），子进程运行命令里不应当带有 "--resume" 标志。
    模拟数据：session_id = None
    预期结果：拼装给 Popen 执行的 cmd 数组中不包含 "--resume"。
    """
    proc = _make_proc(stdout_lines=[_result_line()])
    with patch("subprocess.Popen", return_value=proc) as mock_popen:
        cc.run_claude("test", session_id=None, idle_timeout=300)

    cmd = mock_popen.call_args[0][0]
    assert "--resume" not in cmd
