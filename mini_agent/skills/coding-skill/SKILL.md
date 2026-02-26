---
name: coding-skill
description: 当用户提到 coding、编程、写代码、claude code、代码分析、代码调试、帮我写程序、代码优化、代码审查时使用此 skill。封装 Claude Code CLI 流式输出的格式化对话工具，提供结构化的格式化输出（区分思考过程、工具调用、结果），支持交互式多轮对话和单次问答两种模式, 默认使用交互式多轮对话（即使用最新session id）。
---

# Coding Skill

## Overview

通过 BashTool 调用 `scripts/claude_chat.py` 与 Claude Code CLI 交互。所有 session 自动持久化到 `assets/session.json`。

## 前置条件

- `claude` CLI 在 PATH 中
- Python 3.11+

## 调用方式

### 默认：继续上次对话

不传任何 session 参数，脚本自动从 `assets/session.json` 读取最近的 session 继续对话：

```bash
python scripts/claude_chat.py "用户的问题"
```

### 新建 session

传 `--new` 强制新建：

```bash
python scripts/claude_chat.py --new "用户的问题"
```

### 恢复指定 session

从 `assets/session.json` 中找到目标 session_id，传 `--resume`：

```bash
python scripts/claude_chat.py --resume <session_id> "用户的问题"
```

## 新建/续接判断规则

**默认续接，以下情况新建 session（传 `--new`）：**

| 触发条件 | 用户表述示例 |
|----------|-------------|
| 明确要求新对话 | "新问题"、"换个话题"、"重新开始"、"开个新会话" |
| 话题与当前 session 无关 | 当前 session 在讨论数据库优化，用户问"帮我写个爬虫" |
| `assets/session.json` 中最近 session 超过 24 小时未更新 | 检查 `updated_at` 字段 |

**以下情况恢复旧 session（传 `--resume <id>`）：**

| 触发条件 | 用户表述示例 |
|----------|-------------|
| 用户提到之前的对话 | "回到之前那个xxx"、"上次讨论的那个"、"继续之前的优化" |

判断步骤：
1. 读取 `assets/session.json`，检查最近 session 的 `last_prompt`、`summary`、`updated_at`
2. 若用户意图与最近 session 相关 → 不传参数（自动续接）
3. 若用户意图与最近 session 无关但提到了历史话题 → 从 session.json 匹配，1.如果匹配到单个summary内容和用户提到的话题接近，→ 传 `--new`; 2.如果匹配到多个session的summary和用户提到的话题接近，则把多个 session id和summary内容列出来让用户检查，让用户指定session;
4. 若用户意图全新或明确要求 → 传 `--new`

## 输出解析

输出末尾固定包含：

```
SESSION_ID: <完整session_id>
```

从此行提取 session_id 用于后续判断（通常无需手动传，脚本会自动写入 session.json）。

## Session 持久化

`assets/session.json` 以 session_id 为 key，记录每个对话的元信息：

```json
{
  "<session_id>": {
    "first_prompt": "首次提问",
    "last_prompt": "最近提问",
    "last_reply_snippet": "最近回复前200字",
    "summary": "一句话概要",
    "created_at": "2026-02-23T14:30:00",
    "updated_at": "2026-02-23T14:35:00",
    "turns": 3,
    "total_tokens": 4500
  }
}
```

每轮对话后自动写入。`summary` 字段由 `scripts/summarize_sessions.py` 填充。

## 摘要脚本

```bash
python scripts/summarize_sessions.py           # 为缺少摘要的 session 生成概要
python scripts/summarize_sessions.py --all      # 重新生成所有摘要
python scripts/summarize_sessions.py --session <id>  # 只总结指定 session
```

## 限制

通过 BashTool 调用时无法流式显示，等进程结束后一次性返回完整输出。

## 超时注意

编程任务通常耗时较长，BashTool 默认 120s 超时可能不够。**调用 coding-skill 时，BashTool 必须设置 `timeout=300`**（最大可设 600）。

示例：
```bash
# BashTool 调用时务必加 timeout
BashTool(command="python scripts/claude_chat.py '帮我重构这个模块'", timeout=300)
```

`claude_chat.py` 自带空闲超时保护（`--idle-timeout`，默认 120s）：当 claude CLI 超过指定秒数没有任何输出时，自动终止进程。可按需调整：

```bash
python scripts/claude_chat.py --idle-timeout 180 "复杂的重构任务"
```

## 参考文档

用户手动使用的交互模式、内置命令等详见 references/user_guide.md。
