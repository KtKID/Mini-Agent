# 日志系统方案：Feishu ↔ Coding Skill 通信链路

## 一、目标

在 feishu 消息到达 → Agent 处理 → BashTool 调用 claude_chat.py → 返回结果的完整链路上添加结构化日志，用于：

1. **通信数据可回放**：记录 Agent 实际传给 BashTool 的命令、claude_chat.py 收到的参数、session 文件操作
2. **用真实数据验证 bug**：从日志中提取实际 `--user` 值，确认 session 隔离是否生效
3. **可通过 config.yaml 开关**：不影响生产环境性能，需要调试时随时启用

---

## 二、config.yaml 配置开关

### 2.1 新增配置项

在 `config.yaml` 顶层新增 `logging` 段：

```yaml
# ===== Logging Configuration =====
logging:
  enabled: true              # 总开关，false 时全部日志关闭
  log_dir: "logs"            # 日志目录（相对于项目根目录）
  log_level: "INFO"          # 日志级别：DEBUG / INFO / WARNING / ERROR
  feishu_logging: true       # Feishu 链路日志（已有 feishu.log，此项控制新增的链路日志点）
  coding_logging: true       # Coding Skill 链路日志（写入 coding.log）
  bash_logging: true         # BashTool 执行日志（写入 feishu.log）
  max_bytes: 10485760        # 单文件大小上限（默认 10MB）
  backup_count: 5            # 轮转保留文件数
```

### 2.2 config.py 新增 LoggingConfig

```python
class LoggingConfig(BaseModel):
    """Logging configuration"""
    enabled: bool = True
    log_dir: str = "logs"
    log_level: str = "INFO"
    feishu_logging: bool = True
    coding_logging: bool = True
    bash_logging: bool = True
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
```

在 `Config` 主类中新增字段：

```python
class Config(BaseModel):
    llm: LLMConfig
    agent: AgentConfig
    tools: ToolsConfig
    feishu: Optional["FeishuConfig"] = None
    logging: LoggingConfig = Field(default_factory=LoggingConfig)  # 新增
```

在 `Config.from_yaml()` 中新增解析：

```python
# Parse logging configuration
logging_data = data.get("logging", {})
logging_config = LoggingConfig(
    enabled=logging_data.get("enabled", True),
    log_dir=logging_data.get("log_dir", "logs"),
    log_level=logging_data.get("log_level", "INFO"),
    feishu_logging=logging_data.get("feishu_logging", True),
    coding_logging=logging_data.get("coding_logging", True),
    bash_logging=logging_data.get("bash_logging", True),
    max_bytes=logging_data.get("max_bytes", 10 * 1024 * 1024),
    backup_count=logging_data.get("backup_count", 5),
)
```

### 2.3 config-example.yaml 新增段

```yaml
# ===== Logging Configuration =====
# 调试用日志，记录 Feishu ↔ Coding Skill 通信链路数据
logging:
  enabled: true              # 总开关
  log_dir: "logs"            # 日志目录
  log_level: "INFO"          # DEBUG 可看到 session 文件读写细节
  feishu_logging: true       # Feishu 消息处理链路
  coding_logging: true       # Coding Skill (claude_chat.py) 执行链路
  bash_logging: true         # BashTool 命令执行日志
  max_bytes: 10485760        # 单文件 10MB
  backup_count: 5            # 保留 5 个轮转文件
```

---

## 三、日志文件布局

```
logs/
├── feishu.log      ← 已有（保持不变），新增链路日志点也写入此文件
└── coding.log      ← 新增，claude_chat.py 子进程的独立日志
```

两个文件通过 `session_id` 字段关联。

---

## 四、配置传递路径

```
config.yaml
    │
    ▼
Config.from_yaml() → Config.logging: LoggingConfig
    │
    ├─→ cli.py: 初始化 feishu logger / bash logger（读 config.logging）
    │     └─ if config.logging.enabled and config.logging.feishu_logging: 启用链路日志
    │     └─ if config.logging.enabled and config.logging.bash_logging:  启用 BashTool 日志
    │
    └─→ claude_chat.py: 独立进程，不能直接读 Config 对象
          └─ 方案 A（推荐）：通过环境变量传递开关
              cli.py 在构造 BashTool 或 system_prompt 时设置：
                os.environ["CODING_LOG_ENABLED"] = "1"
                os.environ["CODING_LOG_LEVEL"] = "DEBUG"
                os.environ["CODING_LOG_DIR"] = str(log_dir)
          └─ 方案 B：通过 --log-level CLI 参数传递
              claude_chat.py 新增 --log-level 参数
```

**推荐方案 A**：环境变量。理由：
- 不污染 claude_chat.py 的用户可见参数
- BashTool 子进程自动继承父进程环境变量
- 支持在 Agent 运行时动态修改（虽然实际不需要）

---

## 五、各层日志点详设

### 层 1：`cli.py` — Agent Factory + Message Handler

**前置条件**：`config.logging.enabled and config.logging.feishu_logging`

| # | 位置 | 日志内容 | 级别 |
|---|------|---------|------|
| L1 | `make_agent()` | `[FACTORY] session_id={session_id} user_context={'injected'\|'none'}` | INFO |
| L2 | `feishu_message_handler` 入口 | `[MSG_IN] open_id={open_id} chat_id={chat_id} session_id={session_id} msg={message[:100]!r}` | INFO |
| L3 | `get_or_create` 后 | `[SESSION] session_id={session_id} is_new={...} has_agent={...}` | INFO |
| L4 | `agent.run()` 结束后 | `[MSG_OUT] session_id={session_id} resp_len={len} resp={resp[:100]!r}` | INFO |
| L5 | `agent.run()` 异常 | `[MSG_ERR] session_id={session_id} error={e}` | ERROR |

```python
# cli.py:654
def make_agent(session_id: str = ""):
    if log_config.enabled and log_config.feishu_logging:
        logger.info(f"[FACTORY] session_id={session_id} "
                     f"user_context={'injected' if session_id else 'none'}")
    ...

# cli.py:678
async def feishu_message_handler(open_id, message, send_fn, chat_id=""):
    session_id = chat_id or open_id
    if log_config.enabled and log_config.feishu_logging:
        logger.info(f"[MSG_IN] open_id={open_id} chat_id={chat_id} "
                     f"session_id={session_id} msg={message[:100]!r}")
    ...
    session = feishu_skill._session_manager.get_or_create(session_id)
    if log_config.enabled and log_config.feishu_logging:
        logger.info(f"[SESSION] session_id={session_id} "
                     f"is_new={session.message_count==0} has_agent={session.agent is not None}")
    ...
    # agent.run() 后
    if log_config.enabled and log_config.feishu_logging:
        logger.info(f"[MSG_OUT] session_id={session_id} "
                     f"resp_len={len(msg.content)} resp={msg.content[:100]!r}")
```

### 层 2：`bash_tool.py` — BashTool 执行

**前置条件**：通过环境变量 `BASH_LOG_ENABLED=1` 传递（cli.py 启动时按 config 设置）

| # | 位置 | 日志内容 | 级别 |
|---|------|---------|------|
| B1 | `execute()` 入口 | `[BASH_EXEC] cmd={command!r} timeout={timeout} bg={run_in_background}` | INFO |
| B2 | `execute()` 返回前 | `[BASH_DONE] exit_code={rc} stdout_len={len} stderr_len={len}` | INFO |
| B3 | `execute()` 超时 | `[BASH_TIMEOUT] cmd={command[:200]!r} timeout={timeout}` | WARNING |

```python
# bash_tool.py — 顶部
import logging
import os
_log = logging.getLogger("mini_agent.feishu")
_bash_log_enabled = os.environ.get("BASH_LOG_ENABLED") == "1"

# bash_tool.py:309
async def execute(self, command, timeout=120, run_in_background=False):
    if _bash_log_enabled:
        _log.info(f"[BASH_EXEC] cmd={command!r} timeout={timeout} bg={run_in_background}")
    ...
    # 正常返回前
    if _bash_log_enabled:
        _log.info(f"[BASH_DONE] exit_code={process.returncode} "
                   f"stdout_len={len(stdout_text)} stderr_len={len(stderr_text)}")
```

### 层 3：`claude_chat.py` — Coding Skill 执行

**前置条件**：环境变量 `CODING_LOG_ENABLED=1`

| # | 位置 | 日志内容 | 级别 |
|---|------|---------|------|
| C1 | `main()` 入口 | `[START] argv={sys.argv}` | INFO |
| C2 | `parse_args()` 后 | `[ARGS] user_id={user_id} resume_id={resume_id} prompt={prompt[:100]!r} idle_timeout={idle_timeout} force_new={force_new}` | INFO |
| C3 | `run_claude()` 入口 | `[RUN] user_id={user_id} session_id={session_id} idle_timeout={idle_timeout} prompt={prompt[:100]!r}` | INFO |
| C4 | `run_claude()` 完成 | `[DONE] session_id={turn.session_id} result={turn.result[:200]!r} tokens={in}↑{out}↓` | INFO |
| C5 | 超时分支 | `[TIMEOUT] idle_timeout={idle_timeout} stderr={stderr[:500]!r}` | WARNING |
| C6 | 错误分支 | `[ERROR] returncode={rc} stderr={stderr[:500]!r}` | WARNING |
| C7 | `update_session()` | `[SESSION_SAVE] file={path} session_id={sid} turns={n} total_tokens={t}` | DEBUG |

```python
# claude_chat.py — 顶部
import logging
import os
from logging.handlers import RotatingFileHandler

def _setup_coding_logger():
    """按环境变量初始化 coding 日志。不设置环境变量时返回空 logger（不输出）。"""
    logger = logging.getLogger("mini_agent.coding")
    if os.environ.get("CODING_LOG_ENABLED") != "1":
        logger.addHandler(logging.NullHandler())
        return logger

    if logger.handlers:
        return logger

    log_dir = Path(os.environ.get("CODING_LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, os.environ.get("CODING_LOG_LEVEL", "INFO"), logging.INFO)

    logger.setLevel(level)
    fh = RotatingFileHandler(
        log_dir / "coding.log",
        maxBytes=int(os.environ.get("CODING_LOG_MAX_BYTES", 10 * 1024 * 1024)),
        backupCount=int(os.environ.get("CODING_LOG_BACKUP_COUNT", 5)),
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)
    return logger

_log = _setup_coding_logger()
```

### 层 4：`session_utils.py` — Session 文件操作

复用 `mini_agent.coding` logger（由 claude_chat.py 初始化，同一进程）。

| # | 位置 | 日志内容 | 级别 |
|---|------|---------|------|
| S1 | `load_sessions()` | `[LOAD] file={sf} user_id={user_id} count={len(result)}` | DEBUG |
| S2 | `save_sessions()` | `[SAVE] file={sf} user_id={user_id} count={len(sessions)}` | DEBUG |

```python
# session_utils.py — 顶部
import logging
_log = logging.getLogger("mini_agent.coding")

def load_sessions(user_id=None):
    sf = get_session_file(user_id)
    ...
    _log.debug(f"[LOAD] file={sf} user_id={user_id} count={len(result)}")
    return result

def save_sessions(sessions, user_id=None):
    sf = get_session_file(user_id)
    _log.debug(f"[SAVE] file={sf} user_id={user_id} count={len(sessions)}")
    ...
```

### 层 5：`session_manager.py`

已有日志 `SessionManager: Created new session with Agent for {session_id}`，无需新增。

---

## 六、环境变量注入点

在 `cli.py` 中，feishu 初始化块内，根据 `config.logging` 设置环境变量：

```python
# cli.py — feishu 初始化块内，make_agent 定义之前
if config.logging.enabled:
    log_config = config.logging
    log_level_name = log_config.log_level.upper()
    log_dir_abs = str(Path(log_config.log_dir).resolve())

    if log_config.bash_logging:
        os.environ["BASH_LOG_ENABLED"] = "1"

    if log_config.coding_logging:
        os.environ["CODING_LOG_ENABLED"] = "1"
        os.environ["CODING_LOG_LEVEL"] = log_level_name
        os.environ["CODING_LOG_DIR"] = log_dir_abs
        os.environ["CODING_LOG_MAX_BYTES"] = str(log_config.max_bytes)
        os.environ["CODING_LOG_BACKUP_COUNT"] = str(log_config.backup_count)
```

---

## 七、完整数据流日志示例

一条飞书消息的完整日志链路（跨两个日志文件）：

```
=== logs/feishu.log ===
14:30:01 [INFO] mini_agent.feishu: FeishuSkill: [RECV] from=ou_abc123 msg_id=om_xxx content='帮我写个排序算法...'
14:30:01 [INFO] mini_agent.feishu: [MSG_IN] open_id=ou_abc123 chat_id= session_id=ou_abc123 msg='帮我写个排序算法'
14:30:01 [INFO] mini_agent.feishu: [FACTORY] session_id=ou_abc123 creating Agent, user_context=injected
14:30:01 [INFO] mini_agent.feishu: [SESSION] session_id=ou_abc123 is_new=True has_agent=True
14:30:02 [INFO] mini_agent.feishu: [BASH_EXEC] cmd='python claude_chat.py --user ou_abc123 "帮我写个排序算法"' timeout=300 bg=False
14:30:45 [INFO] mini_agent.feishu: [BASH_DONE] exit_code=0 stdout_len=2048 stderr_len=0
14:30:45 [INFO] mini_agent.feishu: [MSG_OUT] session_id=ou_abc123 resp_len=500 resp='排序算法实现如下...'
14:30:45 [INFO] mini_agent.feishu: FeishuSkill: [SENT] open_id=ou_abc123

=== logs/coding.log ===
14:30:02 [INFO] mini_agent.coding: [START] argv=['claude_chat.py', '--user', 'ou_abc123', '帮我写个排序算法']
14:30:02 [INFO] mini_agent.coding: [ARGS] user_id=ou_abc123 resume_id=None prompt='帮我写个排序算法' idle_timeout=120 force_new=False
14:30:02 [DEBUG] mini_agent.coding: [LOAD] file=.../assets/session_ou_abc123.json user_id=ou_abc123 count=0
14:30:02 [INFO] mini_agent.coding: [RUN] user_id=ou_abc123 session_id=None idle_timeout=120 prompt='帮我写个排序算法'
14:30:44 [INFO] mini_agent.coding: [DONE] session_id=abc-def-123 result='这是一个快速排序的实现...' tokens=1200↑350↓
14:30:44 [DEBUG] mini_agent.coding: [SAVE] file=.../assets/session_ou_abc123.json user_id=ou_abc123 count=1
14:30:44 [DEBUG] mini_agent.coding: [SESSION_SAVE] file=.../assets/session_ou_abc123.json session_id=abc-def-123 turns=1 total_tokens=1550
```

---

## 八、用日志验证 bug 的方法

| 验证项 | 检查方式 | 期望结果 |
|--------|---------|---------|
| `--user` 是否传递 | `coding.log` grep `[ARGS]` 检查 `user_id` | 非 None，与 feishu open_id/chat_id 一致 |
| session 文件隔离 | `coding.log` grep `[LOAD]/[SAVE]` 检查 file 路径 | 不同用户 → 不同文件名 |
| session 续接正确 | `coding.log` grep `[RUN]` 检查 `session_id` | 第二次对话应有 session_id（非 None） |
| factory keyword arg | `feishu.log` grep `[FACTORY]` | `session_id=ou_xxx` 非空 |
| BashTool 实际命令 | `feishu.log` grep `[BASH_EXEC]` | 包含 `--user ou_xxx` |
| idle-timeout 生效 | `coding.log` grep `[TIMEOUT]` | 仅在实际超时时出现 |
| stderr 捕获 | `coding.log` grep `[ERROR]` | claude CLI 报错时有 stderr 内容 |
| 两用户互不干扰 | grep 两个不同 user_id 的 `[LOAD]/[SAVE]` | 文件路径完全不同 |

---

## 九、用真实数据构造测试用例

从日志提取真实飞书 ID 后，构造对应测试：

```python
# tests/coding/test_real_data.py
"""用真实飞书数据格式验证 session 隔离。

测试数据来源：从 logs/feishu.log 和 logs/coding.log 提取的实际参数。
"""

# 真实飞书 ID 格式示例（脱敏）
PRIVATE_CHAT = {
    "open_id": "ou_abc123def456ghi789",
    "chat_id": "",
    "session_id": "ou_abc123def456ghi789",  # 私聊: chat_id 为空，用 open_id
    "session_file": "session_ou_abc123def456ghi789.json",
}

GROUP_CHAT = {
    "open_id": "ou_abc123def456ghi789",
    "chat_id": "oc_groupchat123456789",
    "session_id": "oc_groupchat123456789",  # 群聊: 用 chat_id
    "session_file": "session_oc_groupchat123456789.json",
}

def test_private_chat_session_file(cc, tmp_assets_dir):
    """私聊场景：session_id = open_id → session_ou_xxx.json"""
    d = PRIVATE_CHAT
    cc.save_sessions({"s1": {"first_prompt": "test"}}, user_id=d["session_id"])
    assert (tmp_assets_dir / d["session_file"]).exists()

def test_group_chat_session_file(cc, tmp_assets_dir):
    """群聊场景：session_id = chat_id → session_oc_xxx.json"""
    d = GROUP_CHAT
    cc.save_sessions({"s1": {"first_prompt": "test"}}, user_id=d["session_id"])
    assert (tmp_assets_dir / d["session_file"]).exists()

def test_private_and_group_isolated(cc, tmp_assets_dir):
    """同一用户的私聊和群聊 session 互相隔离。"""
    cc.save_sessions({"s_priv": {"first_prompt": "私聊"}}, user_id=PRIVATE_CHAT["session_id"])
    cc.save_sessions({"s_grp": {"first_prompt": "群聊"}}, user_id=GROUP_CHAT["session_id"])
    assert "s_priv" in cc.load_sessions(user_id=PRIVATE_CHAT["session_id"])
    assert "s_grp" in cc.load_sessions(user_id=GROUP_CHAT["session_id"])
    assert "s_grp" not in cc.load_sessions(user_id=PRIVATE_CHAT["session_id"])

def test_safe_id_real_feishu_format(cc):
    """真实飞书 ID 格式（ou_xxx, oc_xxx）经过 _safe_id 后保持不变。"""
    assert cc._safe_id("ou_abc123def456") == "ou_abc123def456"
    assert cc._safe_id("oc_groupchat789") == "oc_groupchat789"
```

---

## 十、改动文件清单

| 文件 | 改动 | 新增行数(估) |
|------|------|-------------|
| `mini_agent/config.py` | 新增 `LoggingConfig` 类 + `Config.logging` 字段 + 解析逻辑 | ~20 行 |
| `mini_agent/config/config-example.yaml` | 新增 `logging:` 配置段 | ~12 行 |
| `mini_agent/cli.py` | 环境变量注入 + 5 个 `logger.info()` | ~25 行 |
| `mini_agent/tools/bash_tool.py` | 3 个日志点 | ~10 行 |
| `mini_agent/skills/coding-skill/scripts/claude_chat.py` | `_setup_coding_logger()` + 7 个日志点 | ~35 行 |
| `mini_agent/skills/coding-skill/scripts/session_utils.py` | 2 个 `_log.debug()` | ~5 行 |
| `tests/coding/test_real_data.py` | 真实数据格式测试 | ~40 行 |

总计约 **~150 行**，**16 个日志点**，完整覆盖 feishu → coding 全链路。

---

## 十一、关闭日志

```yaml
# config.yaml — 生产环境关闭全部调试日志
logging:
  enabled: false
```

或仅关闭某一层：

```yaml
logging:
  enabled: true
  coding_logging: false   # 仅关闭 claude_chat.py 子进程日志
  bash_logging: false     # 仅关闭 BashTool 命令日志
  feishu_logging: true    # 保留 feishu 链路日志
```
