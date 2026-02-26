"""handle_command() 内部斜线命令的处理测试。

现有的测试仅覆盖带用户隔离功能的 /sessions 命令。
此文件补充测试其余命令：/new、/session、/help，以及对未知命令和大小写的处理。
"""


def test_new_returns_none_session(cc):
    """
    测试说明：测试 /new 命令的目的是“开启新对话”，此时应丢弃当前 session 状态。
    模拟数据：
      - cmd = "/new"
      - current session_id = "existing-sid"
    预期结果：由 handle_command 处理完毕 (handled=True)，返回的新 session_id 为 None (重置当前对话)。
    """
    handled, sid = cc.handle_command("/new", "existing-sid")
    assert handled is True
    assert sid is None


def test_session_shows_id(cc, capsys):
    """
    测试说明：测试 /session 命令在当前已有进行中对话时的输出表现。
    模拟数据：
      - cmd = "/session"
      - current session_id = "abc-123-def"
    预期结果：已处理 (handled=True)，不改变原 session_id，并在 stdout 中打印当前 session ID 供用户查看。
    """
    handled, sid = cc.handle_command("/session", "abc-123-def")
    assert handled is True
    assert sid == "abc-123-def"
    captured = capsys.readouterr().out
    assert "abc-123-def" in captured


def test_session_no_session(cc, capsys):
    """
    测试说明：测试 /session 命令在当前并无进行的对话时的表现。
    模拟数据：
      - cmd = "/session"
      - current session_id = None
    预期结果：已处理 (handled=True)，依旧无 session_id，并在 stdout 中提示用户暂无对话。
    """
    handled, sid = cc.handle_command("/session", None)
    assert handled is True
    assert sid is None
    captured = capsys.readouterr().out
    assert "暂无" in captured


def test_help_shows_commands(cc, capsys):
    """
    测试说明：测试 /help 帮助命令输出所有支持的内置斜线命令罗列。
    模拟数据：cmd = "/help"
    预期结果：已处理，stdout 输出了说明文档（包含 /new, /sessions, /help）。
    """
    handled, _ = cc.handle_command("/help", None)
    assert handled is True
    captured = capsys.readouterr().out
    assert "/new" in captured
    assert "/sessions" in captured
    assert "/help" in captured


def test_unknown_command_not_handled(cc):
    """
    测试说明：测试未识别或拼写错误的自定义命令行为。如果是未注册命令，应该被当作普通对话给 Claude 处理。
    模拟数据：
      - cmd = "/foo"
      - current session = "keep-sid"
    预期结果：未内部处理 (handled=False)，session_id 原样保留，外层代码将把这行发送给 LLM。
    """
    handled, sid = cc.handle_command("/foo", "keep-sid")
    assert handled is False
    assert sid == "keep-sid"


def test_case_insensitive(cc):
    """
    测试说明：测试用户输入的大写/大小写混写斜线命令是否仍然能被正确识别。
    模拟数据：cmd = "/NEW" 和 "/HELP"
    预期结果：能被当成 /new 和 /help 正常处理 (handled=True)。
    """
    handled, sid = cc.handle_command("/NEW", "sid")
    assert handled is True
    assert sid is None  # /new 会重置 session

    handled, _ = cc.handle_command("/HELP", None)
    assert handled is True
