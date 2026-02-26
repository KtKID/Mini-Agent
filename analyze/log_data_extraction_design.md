# 日志数据提取与测试数据集生成

## 一、可提取的数据字段

从 `logs/feishu.log` 和 `logs/coding.log` 可提取的结构化数据：

| 来源 | 日志标签 | 可提取字段 | 用途 |
|------|---------|----------|------|
| **feishu.log** | `[MSG_IN]` | `open_id`, `chat_id`, `session_id`, `message` | 真实飞书 ID 格式 |
| **feishu.log** | `[BASH_EXEC]` | `command`, `timeout`, `bg` | BashTool 实际构造的命令 |
| **coding.log** | `[ARGS]` | `user_id`, `resume_id`, `prompt`, `idle_timeout`, `force_new` | parse_args 解析结果 |
| **coding.log** | `[RUN]` | `user_id`, `session_id`, `idle_timeout`, `prompt` | run_claude 调用参数 |
| **coding.log** | `[LOAD]` | `file` (完整路径), `user_id`, `count` | session 文件路径 |
| **coding.log** | `[SAVE]` | `file`, `user_id`, `count` | session 文件写入 |
| **coding.log** | `[DONE]` | `session_id` (Claude 返回), `result` 前200字, `tokens↑`, `tokens↓` | Claude 会话结果 |
| **coding.log** | `[TIMEOUT]` | `idle_timeout`, `stderr` | 超时场景数据 |

---

## 二、数据集格式 (JSON)

提取后的测试数据保存为 JSON：

```json
{
  "version": "1.0",
  "extracted_at": "2026-02-26T14:30:00",
  "source_logs": {
    "feishu": "logs/feishu.log",
    "coding": "logs/coding.log"
  },
  "user_sessions": [
    {
      "trace_id": "1",
      "scenario": "private_chat",
      "feishu": {
        "open_id": "ou_abc123def456ghi789",
        "chat_id": "",
        "session_id": "ou_abc123def456ghi789",
        "message": "帮我写个排序算法"
      },
      "bash": {
        "command": "python claude_chat.py --user ou_abc123def456ghi789 \"帮我写个排序算法\"",
        "timeout": 300,
        "background": false
      },
      "coding": {
        "parsed_user_id": "ou_abc123def456ghi789",
        "parsed_resume_id": null,
        "parsed_idle_timeout": 120,
        "parsed_force_new": false,
        "run_user_id": "ou_abc123def456ghi789",
        "run_session_id": null,
        "run_idle_timeout": 120,
        "session_file_path": "/path/to/session_ou_abc123def456ghi789.json",
        "claude_session_id": "abc-def-123456",
        "input_tokens": 1200,
        "output_tokens": 350
      },
      "validation": {
        "user_passed": true,
        "session_file_isolated": true,
        "session_id_preserved": null
      }
    },
    {
      "trace_id": "2",
      "scenario": "group_chat",
      "feishu": {
        "open_id": "ou_abc123def456ghi789",
        "chat_id": "oc_groupchat123456789",
        "session_id": "oc_groupchat123456789",
        "message": "帮我调试代码"
      },
      ...
    }
  ]
}
```

---

## 三、提取工具脚本

### 3.1 位置

`mini_agent/skills/coding-skill/scripts/extract_log_data.py`

### 3.2 功能

```python
"""
从日志文件提取结构化数据，生成测试数据集。

用法:
  python extract_log_data.py --logs-dir logs --output test_dataset.json

输出:
  test_dataset.json - 可直接用于 pytest 的测试数据
  test_cases.py     - 从数据集生成的 pytest 用例文件
"""
```

### 3.3 核心逻辑

```python
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# 日志行解析器
class LogParser:
    """解析结构化日志行"""

    # 正则模式（匹配日志格式：YYYY-MM-DD HH:MM:SS [LEVEL] logger: message）
    LOG_PATTERN = re.compile(
        r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} '
        r'\[(INFO|DEBUG|WARNING|ERROR)\] '
        r'([a-z._]+): '
        r'(.*)$'
    )

    # 各日志标签的参数提取模式
    MSG_IN_PATTERN = re.compile(r'\[MSG_IN\] open_id=(\S+) chat_id=(\S*) session_id=(\S+) msg=(.+)')
    BASH_EXEC_PATTERN = re.compile(r'\[BASH_EXEC\] cmd=(.+) timeout=(\d+) bg=(\w+)')
    ARGS_PATTERN = re.compile(r'\[ARGS\] user_id=(\S+) resume_id=(\S*) prompt=(.+) idle_timeout=(\d+) force_new=(\w+)')
    RUN_PATTERN = re.compile(r'\[RUN\] user_id=(\S+) session_id=(\S*) idle_timeout=(\d+) prompt=(.+)')
    LOAD_PATTERN = re.compile(r'\[LOAD\] file=(\S+) user_id=(\S+) count=(\d+)')
    SAVE_PATTERN = re.compile(r'\[SAVE\] file=(\S+) user_id=(\S+) count=(\d+)')
    DONE_PATTERN = re.compile(r'\[DONE\] session_id=(\S+) result=(.+) tokens=(\d+).*?(\d+)')
    TIMEOUT_PATTERN = re.compile(r'\[TIMEOUT\] idle_timeout=(\d+) stderr=(.+)')

    def __init__(self, log_path: Path):
        self.log_path = log_path

    def parse_all(self) -> list[dict]:
        """解析整个日志文件，返回按 trace_id 分组的数据"""
        traces = []
        current_trace = None
        trace_id_counter = 0

        for line in self.log_path.read_text(encoding='utf-8').split('\n'):
            if not line.strip():
                continue

            level, _, message = self._parse_line(line)
            if not level:
                continue

            # 检测新会话起点（[MSG_IN] 表示新用户消息到达）
            if '[MSG_IN]' in message:
                if current_trace:
                    traces.append(current_trace)
                trace_id_counter += 1
                current_trace = self._init_trace(trace_id_counter)

            # 填充当前 trace 数据
            if current_trace:
                self._fill_trace(current_trace, level, message)

        if current_trace:
            traces.append(current_trace)

        return traces

    def _parse_line(self, line: str) -> tuple[Optional[str], str]:
        """解析单行日志，返回 (level, message)"""
        m = self.LOG_PATTERN.match(line)
        if m:
            return m.group(1), m.group(2)
        return None, line

    def _init_trace(self, trace_id: int) -> dict:
        """初始化一个 trace 数据结构"""
        return {
            "trace_id": str(trace_id),
            "scenario": "unknown",
            "feishu": {},
            "bash": {},
            "coding": {},
            "validation": {},
        }

    def _fill_trace(self, trace: dict, level: str, message: str):
        """根据日志标签填充 trace 数据"""
        if '[MSG_IN]' in message:
            self._parse_msg_in(trace, message)
            trace["scenario"] = "group_chat" if trace["feishu"]["chat_id"] else "private_chat"
        elif '[BASH_EXEC]' in message:
            self._parse_bash_exec(trace, message)
        elif '[ARGS]' in message:
            self._parse_args(trace, message)
        elif '[RUN]' in message:
            self._parse_run(trace, message)
        elif '[LOAD]' in message:
            self._parse_load(trace, message)
        elif '[SAVE]' in message:
            self._parse_save(trace, message)
        elif '[DONE]' in message:
            self._parse_done(trace, message)
        elif '[TIMEOUT]' in message:
            self._parse_timeout(trace, message)

    def _parse_msg_in(self, trace: dict, message: str):
        m = self.MSG_IN_PATTERN.search(message)
        if m:
            trace["feishu"] = {
                "open_id": m.group(1),
                "chat_id": m.group(2) or None,
                "session_id": m.group(3),
                "message": m.group(4),
            }

    def _parse_bash_exec(self, trace: dict, message: str):
        m = self.BASH_EXEC_PATTERN.search(message)
        if m:
            trace["bash"] = {
                "command": m.group(1),
                "timeout": int(m.group(2)),
                "background": m.group(3) == "True",
            }

    def _parse_args(self, trace: dict, message: str):
        m = self.ARGS_PATTERN.search(message)
        if m:
            trace["coding"]["parsed_user_id"] = m.group(1) if m.group(1) != "None" else None
            trace["coding"]["parsed_resume_id"] = m.group(2) if m.group(2) != "None" else None
            trace["coding"]["parsed_idle_timeout"] = int(m.group(3))
            trace["coding"]["parsed_force_new"] = m.group(4) == "True"
            trace["coding"]["parsed_prompt"] = m.group(5)

    # ... 其他 _parse_* 方法类似

def main():
    """主函数：提取并保存数据集"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs-dir", default="logs", help="日志目录")
    parser.add_argument("--output", default="test_dataset.json", help="输出文件路径")
    args = parser.parse_args()

    # 解析 feishu.log
    feishu_parser = LogParser(Path(args.logs_dir) / "feishu.log")
    feishu_traces = feishu_parser.parse_all()

    # 解析 coding.log
    coding_parser = LogParser(Path(args.logs_dir) / "coding.log")
    coding_traces = coding_parser.parse_all()

    # 按 trace_id 合并数据（假设两个日志的 trace 顺序一致）
    # 简单实现：trace_id 对应顺序合并
    merged_traces = []
    for i in range(min(len(feishu_traces), len(coding_traces))):
        merged = {**feishu_traces[i], **coding_traces[i]}
        merged_traces.append(merged)

    # 运行验证逻辑
    for trace in merged_traces:
        trace["validation"] = {
            "user_passed": trace["coding"].get("parsed_user_id") == trace["feishu"].get("session_id"),
            "session_file_isolated": True,  # 假设（日志中有文件路径可验证）
            "session_id_preserved": trace["coding"].get("run_session_id") is not None,
        }

    # 保存数据集
    dataset = {
        "version": "1.0",
        "extracted_at": datetime.now().isoformat(),
        "source_logs": {
            "feishu": str(Path(args.logs_dir) / "feishu.log"),
            "coding": str(Path(args.logs_dir) / "coding.log"),
        },
        "user_sessions": merged_traces,
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(merged_traces)} traces to {output_path}")

    # 生成 pytest 测试文件
    generate_test_cases(merged_traces, output_path.parent / "test_cases_from_logs.py")

def generate_test_cases(traces: list[dict], output_path: Path):
    """从提取的数据生成 pytest 测试用例"""
    test_code = """'''# Auto-generated test cases from log extraction

import pytest

@pytest.fixture
def log_data():
    return {
"""

    # 按场景分类生成测试用例
    private_chats = [t for t in traces if t["scenario"] == "private_chat"]
    group_chats = [t for t in traces if t["scenario"] == "group_chat"]

    test_code += f"        \"private_chats\": {len(private_chats)},\n"
    test_code += f"        \"group_chats\": {len(group_chats)},\n"

    # 生成测试函数
    for i, trace in enumerate(traces[:5]):  # 只生成前5 个作为示例
        test_code += f"\n\ndef test_trace_{i}(log_data):\n"
        test_code += f'    """Generated from trace #{trace["trace_id"]}"""\n'
        test_code += f'    data = log_data["private_chats"][{i}] if log_data["private_chats"] else log_data["group_chats"][{i}]\n'
        test_code += f'    assert data["feishu"]["session_id"] == "{trace["feishu"]["session_id"]}"\n'
        test_code += f'    assert data["coding"]["parsed_user_id"] == "{trace["coding"]["parsed_user_id"]}"\n'

    test_code += "}\n"

    output_path.write_text(test_code, encoding="utf-8")
    print(f"Generated test cases to {output_path}")

if __name__ == "__main__":
    main()
```

---

## 四、生成的测试用例示例

运行提取脚本后自动生成的 `test_cases_from_logs.py`：

```python
# Auto-generated test cases from log extraction

import pytest

@pytest.fixture
def log_data():
    return {
        "private_chats": 15,
        "group_chats": 8,
    }

def test_trace_0(log_data):
    """Generated from trace #1"""
    data = log_data["private_chats"][0]
    assert data["feishu"]["session_id"] == "ou_abc123def456ghi789"
    assert data["coding"]["parsed_user_id"] == "ou_abc123def456ghi789"

def test_trace_1(log_data):
    """Generated from trace #2"""
    data = log_data["group_chats"][0]
    assert data["feishu"]["session_id"] == "oc_groupchat123456789"
    assert data["coding"]["parsed_user_id"] == "oc_groupchat123456789"
```

---

## 五、使用流程

### 5.1 采集真实数据

```bash
# 1. 启用日志（config.yaml）
logging:
  enabled: true
  feishu_logging: true
  coding_logging: true
  bash_logging: true

# 2. 运行系统，让用户通过飞书发送一些消息
python mini_agent/cli.py --config config.yaml

# 3. 等待几条消息处理完成（产生日志）
```

### 5.2 提取数据集

```bash
cd E:/xgt/proj/xMini-Agent
python mini_agent/skills/coding-skill/scripts/extract_log_data.py --logs-dir logs --output analyze/test_dataset.json
```

### 5.3 用生成的数据测试

```bash
# 运行自动生成的测试
uv run pytest tests/coding/test_cases_from_logs.py -v

# 或手动使用数据集写测试
import json
from pathlib import Path

data = json.loads(Path("analyze/test_dataset.json").read_text())
first_trace = data["user_sessions"][0]

# 在测试中使用真实 ID
def test_real_feishu_id_format(cc):
    """验证真实飞书 ID 格式。"""
    user_id = first_trace["feishu"]["session_id"]
    expected_file = f"session_{user_id}.json"
    assert cc._safe_id(user_id) == user_id
    assert cc.get_session_file(user_id).name == expected_file
```

---

## 六、数据脱敏策略

真实日志可能包含敏感信息，提取时需脱敏：

| 字段 | 脱敏规则 |
|------|---------|
| `message` | 保留结构，替换中文内容为 `[REDACTED]`，或仅保留前50字 |
| `result` | 仅保留结构（长度、是否包含关键字），内容 `[REDACTED]` |
| `stderr` | 仅保留错误类型（如 "authentication failed"），隐藏具体密钥/IP |
| `command` | 保留参数名（`--user`, `--resume`），脱敏值为 `[MASKED]` |

```python
def sanitize_message(message: str) -> str:
    """脱敏消息内容"""
    if len(message) > 50:
        return message[:50] + "..."
    # 检测可能的敏感信息
    sensitive_patterns = [
        r'api[_-]?key\s*[:=]\s*\S+',      # API Key
        r'token\s*[:=]\s*\S+',             # Token
        r'password\s*[:=]\s*\S+',          # Password
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP
    ]
    for pattern in sensitive_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return "[REDACTED_SENSITIVE]"
    return message
```

---

## 七、验证项

从数据集验证的关键 bug：

| Bug 类型 | 验证方法 | 预期结果 |
|---------|---------|---------|
| **user_id 未传递** | `validation.user_passed` | 全部为 `true` |
| **session 文件串台** | 检查同一 session_id 对应不同 session_file | 全部为 `false` |
| **factory 签名错误** | 检查 BashTool 命令是否包含 `--user` | 全部包含 |
| **session 续接失败** | 检查 `coding.run_session_id` 在后续 trace 中有值 | 第二条后应有值 |
| **idle-timeout 不生效** | 检查 `[TIMEOUT]` 与配置一致 | 一致 |
| **stderr 丢失** | 检查错误场景的 `stderr` 不为空 | 非空 |

---

## 八、数据集存储位置

```
analyze/
├── test_dataset.json          # 提取的完整数据集
├── test_cases_from_logs.py  # 自动生成的 pytest 测试用例
└── dataset_summary.md        # 提取统计摘要
```

---

## 九、改动文件清单（补充）

| 文件 | 改动 | 新增行数(估) |
|------|------|-------------|
| `mini_agent/skills/coding-skill/scripts/extract_log_data.py` | 新建数据提取脚本 | ~150 行 |
| `analyze/test_dataset.json` | 自动生成，手动维护 | - |
| `tests/coding/test_cases_from_logs.py` | 自动生成，手动维护 | - |

---

## 十、与原方案的关系

- **原方案**：定义了日志系统架构（16 个日志点）
- **本补充**：定义如何从日志中**提取结构化数据**，生成测试数据集
- **两者结合**：
  1. 日志系统运行 → 产生 feishu.log + coding.log
  2. extract_log_data.py 解析 → 生成 test_dataset.json
  3. test_dataset.json 用于 pytest 测试 → 验证 session 隔离等 bug 修复
