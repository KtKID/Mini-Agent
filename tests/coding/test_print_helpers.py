"""_print_summary, _print_tool_use, _print_tool_result 打印辅助函数的测试。

这些函数用于格式化终端输出，包含 ANSI 颜色和截断逻辑。
所有测试均使用 capsys 来捕获 stdout 进行验证。
"""


# ── _print_summary ──────────────────────────────────────────────────────


def test_print_summary_with_tokens(cc, capsys):
    """
    测试说明：当 Turn 对象包含累计的 Token 数据时，摘要输出应包含 Token 计数信息。
    模拟数据：
      - turn.cumulative_input_tokens = 500
      - turn.cumulative_output_tokens = 200
    预期结果：stdout 捕获中包含 "500" 和 "200"。
    """
    turn = cc.Turn()
    turn.cumulative_input_tokens = 500
    turn.cumulative_output_tokens = 200
    cc._print_summary(turn)
    captured = capsys.readouterr().out
    assert "500" in captured
    assert "200" in captured


def test_print_summary_with_session(cc, capsys):
    """
    测试说明：当 Turn 对象包含 session_id 时，输出中应显示该 SESSION_ID。
    模拟数据：turn.session_id = "abcdef-1234-5678"
    预期结果：stdout 捕获中包含 "SESSION_ID:" 和完整的 ID。
    """
    turn = cc.Turn()
    turn.session_id = "abcdef-1234-5678"
    cc._print_summary(turn)
    captured = capsys.readouterr().out
    assert "SESSION_ID:" in captured
    assert "abcdef-1234-5678" in captured


def test_print_summary_empty_turn(cc, capsys):
    """
    测试说明：当 Turn 对象为空（没有收集到任何数据）时，调用时不应崩溃，且仍会打印分隔线。
    模拟数据：空的 cc.Turn() 对象
    预期结果：代码正常执行，且 stdout 中包含分隔线字符 "─"。
    """
    turn = cc.Turn()
    cc._print_summary(turn)
    captured = capsys.readouterr().out
    assert "─" in captured  # separator line


def test_print_summary_with_tools(cc, capsys):
    """
    测试说明：当 Turn 对象中记录了调用的工具列表时，输出中应当列出这些工具的名称。
    模拟数据：turn.tool_uses = [{"name": "bash"}, {"name": "read_file"}]
    预期结果：stdout 捕获中包含 "bash" 和 "read_file"。
    """
    turn = cc.Turn()
    turn.tool_uses = [{"name": "bash"}, {"name": "read_file"}]
    cc._print_summary(turn)
    captured = capsys.readouterr().out
    assert "bash" in captured
    assert "read_file" in captured


# ── _print_tool_use ─────────────────────────────────────────────────────


def test_print_tool_use_truncation(cc, capsys):
    """
    测试说明：当工具参数输入值过长（超过 200 字符）时，输出中应将其截断以避免刷屏。
    模拟数据：tool = {"name": "write_file", "input": {"content": "x" * 300}}
    预期结果：输出包含工具名 "write_file" 和截断省略符 "…"。
    """
    tool = {
        "name": "write_file",
        "input": {"content": "x" * 300},
    }
    cc._print_tool_use(tool)
    captured = capsys.readouterr().out
    assert "write_file" in captured
    assert "…" in captured


def test_print_tool_use_short_input(cc, capsys):
    """
    测试说明：当工具参数输入值较短（未超过 200 字符）时，应完整显示而不截断。
    模拟数据：tool = {"name": "bash", "input": {"command": "ls -la"}}
    预期结果：输出包含工具名和完整参数名 "ls -la"，并且该行不包含截断符 "…"。
    """
    tool = {
        "name": "bash",
        "input": {"command": "ls -la"},
    }
    cc._print_tool_use(tool)
    captured = capsys.readouterr().out
    assert "bash" in captured
    assert "ls -la" in captured
    assert "…" not in captured.split("ls -la")[1] if "ls -la" in captured else True


# ── _print_tool_result ──────────────────────────────────────────────────


def test_print_tool_result_error(cc, capsys):
    """
    测试说明：当传入的工具执行结果表示出错（is_error=True）时，应打印红色错误标签。
    模拟数据：result = {"content": "command failed", "is_error": True}
    预期结果：输出中包含错误符号 "❌" 和文本 "工具错误"。
    """
    result = {"content": "command failed", "is_error": True}
    cc._print_tool_result(result)
    captured = capsys.readouterr().out
    assert "❌" in captured
    assert "工具错误" in captured


def test_print_tool_result_success(cc, capsys):
    """
    测试说明：当传入的工具执行结果表示成功（is_error=False）时，应打印绿色成功标签。
    模拟数据：result = {"content": "file created", "is_error": False}
    预期结果：输出中包含成功符号 "✅" 和文本 "工具结果"。
    """
    result = {"content": "file created", "is_error": False}
    cc._print_tool_result(result)
    captured = capsys.readouterr().out
    assert "✅" in captured
    assert "工具结果" in captured


def test_print_tool_result_truncation(cc, capsys):
    """
    测试说明：当工具结果内容超长（超过 400 字符）时，打印时应在末尾保留省略提示信息。
    模拟数据：result = {"content": "x" * 600, "is_error": False}
    预期结果：输出中包含截断说明文字 "省略"。
    """
    result = {"content": "x" * 600, "is_error": False}
    cc._print_tool_result(result)
    captured = capsys.readouterr().out
    assert "省略" in captured
