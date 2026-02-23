---
name: coding-skill
description: 当用户提到 coding、编程、写代码、claude code、代码分析、代码调试、帮我写程序、代码优化、代码审查时使用此 skill。封装 Claude Code CLI 流式输出的格式化对话工具，提供结构化的格式化输出（区分思考过程、工具调用、结果），支持交互式多轮对话和单次问答两种模式。
---

# Coding Skill

## Overview

本 skill 提供 `claude_chat.py` 脚本，封装 Claude Code CLI 的 `stream-json` 输出，将原始 JSON 流解析为格式化的终端输出，并支持基于 session 的多轮对话。所有 session 记录自动持久化到 `assets/session.json`。

## 前置条件

- `claude` CLI 已安装且在 PATH 中（`which claude` 可找到）
- Python 3.11+

## 使用方式

### 默认行为：自动继续上次对话

所有调用方式默认继续 `assets/session.json` 中最近的 session。只有显式传 `--new` 才新建 session。

### 直接终端运行（用户手动使用）

```bash
# 继续上次对话（默认，无历史则自动新建）
python scripts/claude_chat.py "帮我优化那个函数"

# 强制新建 session
python scripts/claude_chat.py --new "全新的问题"

# 继续指定 session
python scripts/claude_chat.py --resume <session_id> "回到之前的话题"

# 交互模式（自动恢复上次 session）
python scripts/claude_chat.py
```

交互模式内置命令:

| 命令 | 说明 |
|------|------|
| `/new` | 开启新对话 |
| `/session` | 显示当前 session ID |
| `/sessions` | 列出所有已保存的 session |
| `/help` | 显示帮助 |
| `exit` / `q` | 退出 |

### Agent 调用模式（通过 BashTool）

Agent 无法使用交互模式（stdin 冲突），通过多次单次调用实现多轮对话。

**默认继续上次 session，无需手动传 session_id：**

```bash
# 第1次调用 — 自动继续上次 session（无历史则新建）
python scripts/claude_chat.py "分析 main.py 的架构"

# 第2次调用 — 自动继续同一 session（无需 --resume）
python scripts/claude_chat.py "重点看数据库查询部分"

# 只有需要新话题时才传 --new
python scripts/claude_chat.py --new "完全不相关的新问题"
```

输出末尾包含 `SESSION_ID: <完整ID>`，如需恢复特定旧 session 可用 `--resume <id>`。

读取 `assets/session.json` 可查看所有历史 session 的 ID 和概要。

## 输出格式

| 标记 | 含义 | 颜色 |
|------|------|------|
| 💭 思考中… | thinking 过程 | 灰色 |
| 🔧 工具名 | 工具调用及参数 | 蓝色 |
| ✅ 工具结果 | 工具执行成功 | 绿色 |
| ❌ 工具错误 | 工具执行失败 | 红色 |
| 文字流 | Claude 回复内容 | 青色 |
| 摘要行 | thinking 字数、工具列表、token 用量 | 灰色 |
| `SESSION_ID: xxx` | 完整 session ID（供 Agent 提取） | 无色 |

## Session 持久化

### 数据结构

所有 session 记录保存在 `assets/session.json`，以 session_id 为 key：

```json
{
  "550e8400-e29b-41d4-a716-446655440000": {
    "first_prompt": "分析 main.py 的架构",
    "last_prompt": "重点看数据库查询部分",
    "last_reply_snippet": "数据库查询主要集中在 db/queries.py...",
    "summary": "分析 main.py 架构并优化数据库查询",
    "created_at": "2026-02-23T14:30:00",
    "updated_at": "2026-02-23T14:35:00",
    "turns": 3,
    "total_tokens": 4500
  }
}
```

| 字段 | 说明 |
|------|------|
| `first_prompt` | 该 session 的第一个问题 |
| `last_prompt` | 最近一次提问 |
| `last_reply_snippet` | 最近一次回复的前 200 字符 |
| `summary` | 一句话概要（由 `summarize_sessions.py` 生成） |
| `created_at` | 创建时间 |
| `updated_at` | 最近更新时间 |
| `turns` | 对话轮次 |
| `total_tokens` | 累计 token 用量 |

### 自动写入

每轮对话结束后，`claude_chat.py` 自动将 session 信息写入 `assets/session.json`。`summary` 字段初始为空，由定时任务或手动触发填充。

### 摘要生成

`scripts/summarize_sessions.py` 为缺少摘要的 session 生成一句话概要：

```bash
# 为所有缺少摘要的 session 生成概要
python scripts/summarize_sessions.py

# 重新生成所有摘要
python scripts/summarize_sessions.py --all

# 只总结指定 session
python scripts/summarize_sessions.py --session <session_id>
```

#### 定时执行（每天凌晨 3 点）

```bash
crontab -e
# 添加以下行:
0 3 * * * cd /path/to/Mini-Agent && python mini_agent/skills/coding-skill/scripts/summarize_sessions.py
```

## 限制

当前通过 BashTool 调用时，无法流式显示中间过程。BashTool 等待进程完全结束后才返回完整输出，流式显示仅在直接终端运行时有效。
