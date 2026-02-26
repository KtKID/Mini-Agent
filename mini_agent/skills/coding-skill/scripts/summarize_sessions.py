#!/usr/bin/env python3
"""
summarize_sessions.py - 为 session 文件中缺少摘要的 session 生成概要

用法:
  python scripts/summarize_sessions.py              # 为所有缺少摘要的 session 生成概要
  python scripts/summarize_sessions.py --all         # 重新生成所有 session 的摘要
  python scripts/summarize_sessions.py --session <id> # 只总结指定 session
  python scripts/summarize_sessions.py --user <id>   # 处理指定用户的 session 文件
  python scripts/summarize_sessions.py --all-users   # 遍历所有用户的 session 文件

定时执行（crontab 示例，每天凌晨 3 点）:
  0 3 * * * cd /path/to/Mini-Agent && python mini_agent/skills/coding-skill/scripts/summarize_sessions.py

工作原理:
  读取 session 文件，对每个需要总结的 session:
  1. 用 first_prompt + last_prompt + last_reply_snippet 拼接上下文
  2. 调用 claude -p 生成一句话摘要
  3. 写回 session 文件的 summary 字段
"""

import re
import sys
import json
import subprocess
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SESSION_FILE = ASSETS_DIR / "session.json"


def _safe_id(user_id: str) -> str:
    """将 user_id 转为安全的文件名片段（仅保留字母数字和下划线/连字符）。"""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', user_id)


def get_session_file(user_id: str | None = None) -> Path:
    """根据 user_id 返回对应的 session 文件路径。无 user_id 则返回全局文件（向后兼容）。"""
    if user_id:
        return ASSETS_DIR / f"session_{_safe_id(user_id)}.json"
    return SESSION_FILE


def load_sessions(user_id: str | None = None) -> dict:
    sf = get_session_file(user_id)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_sessions(sessions: dict, user_id: str | None = None) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    sf = get_session_file(user_id)
    sf.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def summarize_one(session_id: str, info: dict) -> str:
    """调用 claude CLI 为一个 session 生成一句话摘要。"""
    first = info.get("first_prompt", "")
    last_p = info.get("last_prompt", "")
    last_r = info.get("last_reply_snippet", "")
    turns = info.get("turns", 0)

    context = (
        f"以下是一个编程对话的信息，请用一句中文（不超过 50 字）概括这个对话的主题。\n"
        f"只输出摘要，不要任何前缀。\n\n"
        f"首次提问: {first}\n"
        f"最近提问: {last_p}\n"
        f"最近回复片段: {last_r[:300]}\n"
        f"总轮次: {turns}"
    )

    try:
        result = subprocess.run(
            ["claude", "-p", context, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:100]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # 降级：用 first_prompt 截断作为摘要
    return first[:50] if first else "(无摘要)"


def process_sessions(sessions: dict, target_id: str | None, do_all: bool) -> int:
    """处理一组 sessions，返回更新数量。"""
    updated = 0
    for sid, info in sessions.items():
        if target_id and sid != target_id:
            continue
        if not do_all and not target_id and info.get("summary"):
            continue

        print(f"总结 session {sid[:8]}… ", end="", flush=True)
        summary = summarize_one(sid, info)
        info["summary"] = summary
        updated += 1
        print(f"→ {summary}")
    return updated


def main() -> None:
    args = sys.argv[1:]
    target_id = None
    do_all = False
    user_id = None
    all_users = False

    i = 0
    while i < len(args):
        if args[i] == "--all":
            do_all = True
            i += 1
        elif args[i] == "--session" and i + 1 < len(args):
            target_id = args[i + 1]
            i += 2
        elif args[i] == "--user" and i + 1 < len(args):
            user_id = args[i + 1]
            i += 2
        elif args[i] == "--all-users":
            all_users = True
            i += 1
        else:
            i += 1

    if all_users:
        # 遍历所有 session_*.json 文件
        session_files = list(ASSETS_DIR.glob("session_*.json")) + (
            [SESSION_FILE] if SESSION_FILE.exists() else []
        )
        if not session_files:
            print("未找到任何 session 文件。")
            return

        total_updated = 0
        for sf in session_files:
            print(f"\n处理文件: {sf.name}")
            try:
                sessions = json.loads(sf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                print(f"  跳过（读取失败）")
                continue
            if not sessions:
                print(f"  跳过（空文件）")
                continue

            updated = process_sessions(sessions, target_id, do_all)
            if updated > 0:
                ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                sf.write_text(
                    json.dumps(sessions, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                total_updated += updated

        print(f"\n共更新 {total_updated} 个 session 的摘要。")
        return

    sessions = load_sessions(user_id)
    if not sessions:
        label = f"session 文件 (user={user_id})" if user_id else "session.json"
        print(f"{label} 为空，无需处理。")
        return

    updated = process_sessions(sessions, target_id, do_all)

    if updated > 0:
        save_sessions(sessions, user_id)
        print(f"\n已更新 {updated} 个 session 的摘要。")
    else:
        print("所有 session 已有摘要，无需更新。")


if __name__ == "__main__":
    main()
