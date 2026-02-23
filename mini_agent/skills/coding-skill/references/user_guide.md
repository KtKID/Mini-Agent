# Claude Chat 用户指南

## 安装前提

- `claude` CLI 已安装且在 PATH 中（`which claude` 可找到）
- Python 3.11+

## 单次问答

```bash
# 继续上次对话（默认）
python scripts/claude_chat.py "帮我优化那个函数"

# 强制新建 session
python scripts/claude_chat.py --new "全新的问题"

# 继续指定 session
python scripts/claude_chat.py --resume <session_id> "回到之前的话题"
```

## 交互模式

```bash
# 启动交互模式（自动恢复上次 session）
python scripts/claude_chat.py

# 强制新 session 进入交互模式
python scripts/claude_chat.py --new
```

启动后显示：

```
Claude Chat  /new 新对话  /sessions 列表  /help 帮助  exit 退出
────────────────────────────────────────────────────────────────

↻ 已恢复上次对话: 分析 main.py 架构
  session: 550e8400… | 3 轮

你 [#0 550e84…]
```

### 内置命令

| 命令 | 说明 |
|------|------|
| `/new` | 丢弃当前 session，开启新对话 |
| `/session` | 显示当前完整 session ID |
| `/sessions` | 列出所有已保存的 session（标记当前活跃的） |
| `/help` | 显示帮助 |
| `exit` / `q` / `退出` | 退出 |

### 提示符含义

```
你 [新]            ← 还没有 session
你 [#1 550e84…]   ← 第1轮，session ID 前6位
你 [#2 550e84…]   ← 第2轮，同一 session
```

## 输出格式

| 标记 | 含义 | 颜色 |
|------|------|------|
| 💭 思考中… | thinking 过程（实时流式） | 灰色 |
| 🔧 工具名 | 工具调用及参数 | 蓝色 |
| ✅ 工具结果 | 工具执行成功（截取400字符） | 绿色 |
| ❌ 工具错误 | 工具执行失败 | 红色 |
| 青色文字流 | Claude 实时回复内容 | 青色 |
| 摘要行 | thinking 字数 / 工具列表 / token 用量 / session ID | 灰色 |
| `SESSION_ID: xxx` | 完整 session ID | 无色 |

## Session 管理

### 自动持久化

每轮对话结束后，session 信息自动写入 `assets/session.json`。

### 查看所有 session

交互模式中输入 `/sessions`，或直接查看 `assets/session.json`。

### 摘要生成

```bash
# 为缺少摘要的 session 生成概要
python scripts/summarize_sessions.py

# 重新生成所有摘要
python scripts/summarize_sessions.py --all

# 只总结指定 session
python scripts/summarize_sessions.py --session <session_id>
```

### 定时总结（每天凌晨 3 点）

```bash
crontab -e
# 添加以下行:
0 3 * * * cd /path/to/Mini-Agent && python mini_agent/skills/coding-skill/scripts/summarize_sessions.py
```

## Session 数据结构

`assets/session.json` 格式：

```json
{
  "<session_id>": {
    "first_prompt": "首次提问",
    "last_prompt": "最近提问",
    "last_reply_snippet": "最近回复前200字",
    "summary": "一句话概要（定时任务填充）",
    "created_at": "2026-02-23T14:30:00",
    "updated_at": "2026-02-23T14:35:00",
    "turns": 3,
    "total_tokens": 4500
  }
}
```
