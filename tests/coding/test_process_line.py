"""process_line() 函数的测试 —— stream-json 解析器的核心。

process_line() 用于解析 claude CLI 输出的每一行 stream-json，
并填充到 Turn 数据类对象中。它处理了各种事件：stream_event（text_delta,
thinking_delta, message_delta, content_block_start）、assistant（tool_use）、
tool_result，以及 result 事件。

所有测试均为纯函数测试 —— 无 I/O，无需 Mock 外部依赖。
"""

import json


# ── Helpers ──────────────────────────────────────────────────────────────


def _stream_event(event: dict, session_id: str = "") -> str:
    """构建一行模拟的 stream_event JSON 数据。"""
    obj = {"type": "stream_event", "event": event}
    if session_id:
        obj["session_id"] = session_id
    return json.dumps(obj)


# ── result event ─────────────────────────────────────────────────────────


def test_result_event(cc):
    """
    测试说明：测试当接收到最外层类型为 "result" 的消息时，是否能正确设置对话的 result 内容、session_id 及其 token 消耗使用情况。
    模拟数据：
      - type: result, result: "answer", session_id: "sid-001"
      - usage: 100 in, 50 out
    预期结果：解析后传入的 turn 对象的属性分别被赋上上述测试值。
    """
    turn = cc.Turn()
    line = json.dumps({
        "type": "result",
        "result": "answer",
        "session_id": "sid-001",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    })
    cc.process_line(line, turn)
    assert turn.result == "answer"
    assert turn.session_id == "sid-001"
    assert turn.usage == {"input_tokens": 100, "output_tokens": 50}


# ── stream_event: content_block_delta ────────────────────────────────────


def test_text_delta(cc):
    """
    测试说明：测试普通的流式纯文本片段（text_delta）能够被正确追加进当前的文本列表中。
    模拟数据：stream_event 内部包装了 content_block_delta，类型为 text_delta 且文本是 "hello"。
    预期结果：turn 对象的 text 字符数组包含 "hello"。
    """
    turn = cc.Turn()
    line = _stream_event({
        "type": "content_block_delta",
        "delta": {"type": "text_delta", "text": "hello"},
    })
    cc.process_line(line, turn)
    assert turn.text == ["hello"]


def test_thinking_delta(cc):
    """
    测试说明：测试模型推理思维过程流式文本片段（thinking_delta）是否被隔离抽取到专用的数组里。
    模拟数据：stream_event 内部包装了 content_block_delta，类型为 thinking_delta 且文本是 "让我想想"。
    预期结果：turn 对象的 thinking 字符数组包含 "让我想想"。
    """
    turn = cc.Turn()
    line = _stream_event({
        "type": "content_block_delta",
        "delta": {"type": "thinking_delta", "thinking": "让我想想"},
    })
    cc.process_line(line, turn)
    assert turn.thinking == ["让我想想"]


# ── stream_event: message_delta (token counting) ────────────────────────


def test_message_delta_tokens(cc):
    """
    测试说明：确保遇到带有用量计数的 message_delta 时，能将其保存到 Turn 对象以备最后总结使用。
    模拟数据：带有关联 token usage {in: 50, out: 30} 信息的 message_delta 流事件。
    预期结果：turn 累计 Token 计数变量（input 和 output）分别记录为 50 和 30。
    """
    turn = cc.Turn()
    line = _stream_event({
        "type": "message_delta",
        "usage": {"input_tokens": 50, "output_tokens": 30},
    })
    cc.process_line(line, turn)
    assert turn.cumulative_input_tokens == 50
    assert turn.cumulative_output_tokens == 30


def test_cumulative_tokens_multi(cc):
    """
    测试说明：测试在一个 Turn 轮次当中由于网络传输多次收到了不同截断阶段流式下发的 usage 统计包时，代码能保证其是被不断叠加取代至正确的最大值的现象。
    模拟数据：两个独立包，第一个包含 usage (50, 30)，第二个包含 (100, 70)。
    预期结果：属性最终结果更新成最后一包，即 150 和 100（这和流协议保持一致，累加发生在上层发送端，接收端直接赋值）。
    备注：根据当前逻辑，代码执行的是累加：`turn.cumulative_input_tokens += tokens`
    """
    turn = cc.Turn()
    for inp, out in [(50, 30), (100, 70)]:
        line = _stream_event({
            "type": "message_delta",
            "usage": {"input_tokens": inp, "output_tokens": out},
        })
        cc.process_line(line, turn)
    # 因为原代码实现是直接 += ，所以 50 + 100 = 150
    assert turn.cumulative_input_tokens == 150
    assert turn.cumulative_output_tokens == 100


# ── stream_event: session_id capture ─────────────────────────────────────


def test_session_id_from_stream_event(cc):
    """
    测试说明：验证第一条出现的流事件是否能成功获取并赋予定位符 ID 以建立联系。
    模拟数据：外层包含 session_id="first-sid" 的第一个 stream_event 对象包。
    预期结果：读取后 turn 对象 session_id == "first-sid"。
    """
    turn = cc.Turn()
    line = _stream_event(
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}},
        session_id="first-sid",
    )
    cc.process_line(line, turn)
    assert turn.session_id == "first-sid"


def test_session_id_not_overwritten(cc):
    """
    测试说明：一回合交互中应该只有首次收到的 ID 被认作真正 ID（避免中间意外包破坏关系）。
    模拟数据：提前将 turn.session_id 写入 "existing-sid"，然后用带 "new-sid" 的流包继续调用解析。
    预期结果：session_id 不改变，依然维持在 "existing-sid"。
    """
    turn = cc.Turn()
    turn.session_id = "existing-sid"
    line = _stream_event(
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}},
        session_id="new-sid",
    )
    cc.process_line(line, turn)
    assert turn.session_id == "existing-sid"


# ── stream_event: content_block_start ────────────────────────────────────


def test_content_block_start_thinking(cc, capsys):
    """
    测试说明：测试遇到 thinking 类型新区块开启时，是否打印相应提示符并且不引发异常。
    模拟数据：type 为内容块开启 content_block_start，其内容块指示类型为 thinking。
    预期结果：能够顺利完成处理流程而不死锁/报错，从虚拟终端(capsys)收集到输出的提示字符 "💭"。
    """
    turn = cc.Turn()
    line = _stream_event({
        "type": "content_block_start",
        "content_block": {"type": "thinking"},
    })
    cc.process_line(line, turn)
    captured = capsys.readouterr().out
    assert "💭" in captured


# ── assistant event (tool_use) ───────────────────────────────────────────


def test_assistant_tool_use(cc):
    """
    测试说明：模拟 Claude 主动提出使用外部工具动作，验证工具名跟入参收集状况。
    模拟数据：最外层消息包 type 是 assistant 返回体，内部包裹了一条工具调用：目标是 bash 执行 ls。
    预期结果：正确将整个 "tool_use" 对象抽取放入了 turn 实例的 tool_uses 列表。
    """
    turn = cc.Turn()
    line = json.dumps({
        "type": "assistant",
        "content": [
            {"type": "tool_use", "name": "bash", "input": {"command": "ls"}},
        ],
    })
    cc.process_line(line, turn)
    assert len(turn.tool_uses) == 1
    assert turn.tool_uses[0]["name"] == "bash"


# ── tool_result event ────────────────────────────────────────────────────


def test_tool_result(cc):
    """
    测试说明：模拟终端向 Claude 回送了工具完成执行后产出结果的动作监听记录。
    模拟数据：消息包类型 type=tool_result，携带执行无误标识 is_error=False，与正常文案 "file created"。
    预期结果：对象内的 tool_results 列表长度符合，内容与期待对等。
    """
    turn = cc.Turn()
    line = json.dumps({
        "type": "tool_result",
        "content": "file created",
        "is_error": False,
    })
    cc.process_line(line, turn)
    assert len(turn.tool_results) == 1
    assert turn.tool_results[0]["content"] == "file created"


# ── Edge cases ───────────────────────────────────────────────────────────


def test_invalid_json_skipped(cc):
    """
    测试说明：系统输入不符合 JSON 序列化法则的乱码/半截数据包。
    模拟数据："this is not json" 字符串
    预期结果：安全拦截 json.JSONDecodeError 相关抛错，平顺抛弃该行，turn 中全部属性不变。
    """
    turn = cc.Turn()
    cc.process_line("this is not json", turn)
    assert turn.result == ""
    assert turn.text == []
    assert turn.tool_uses == []


def test_empty_line_skipped(cc):
    """
    测试说明：处理由 socket 和 stream API 特征带来的心跳产生的换行空格等空响应。
    模拟数据：空字符串 "" 和含仅有空格的 "   "。
    预期结果：无任何处理发生且系统不引发崩溃。
    """
    turn = cc.Turn()
    cc.process_line("", turn)
    cc.process_line("   ", turn)
    assert turn.result == ""
    assert turn.text == []


def test_unknown_type_ignored(cc):
    """
    测试说明：验证系统向前的健壮性，即万一日后 API 下发了目前没有写兼容匹配逻辑的新数据动作时。
    模拟数据：一段有效 JSON 包含非法外围 Type ：“{"type": "some_future_event", "data": 123}”
    预期结果：函数将其视作不需要关心得流动作并继续读取下行，不干扰已拿到的属性。
    """
    turn = cc.Turn()
    line = json.dumps({"type": "some_future_event", "data": 123})
    cc.process_line(line, turn)
    assert turn.result == ""
    assert turn.text == []
    assert turn.tool_uses == []
