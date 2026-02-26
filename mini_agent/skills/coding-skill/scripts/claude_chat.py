#!/usr/bin/env python3
"""
claude_chat.py - 格式化显示 Claude Code 的流式输出，支持多轮对话

默认行为：自动继续上次 session（从 assets/session.json 读取最新的）。
只有显式传 --new 才会创建新 session。

用法:
  python claude_chat.py "问题"                   # 继续上次 session（无历史则新建）
  python claude_chat.py --new "问题"             # 强制新建 session
  python claude_chat.py --resume <id> "问题"     # 继续指定 session
  python claude_chat.py                          # 交互模式（自动恢复上次 session）

交互模式内置命令:
  /new        开启新对话（丢弃当前 session）
  /session    显示当前 session ID
  /sessions   列出所有已保存的 session
  /help       显示帮助
  exit / q    退出
"""

import sys
import json
import subprocess
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ── session.json 路径 ─────────────────────────────────────────────────────
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SESSION_FILE = ASSETS_DIR / "session.json"


# ── ANSI 颜色 ──────────────────────────────────────────────────────────────
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[36m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    RED     = "\033[31m"
    GRAY    = "\033[90m"


# ── 每轮对话收集的数据 ──────────────────────────────────────────────────────
@dataclass
class Turn:
    thinking:     list[str]  = field(default_factory=list)
    text:         list[str]  = field(default_factory=list)
    tool_uses:    list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    result:       str        = ""
    session_id:   str        = ""
    usage:        dict       = field(default_factory=dict)
    # 逐 message 累计 token（从 message_delta 事件收集，比 result.usage 更可靠）
    cumulative_input_tokens:  int = 0
    cumulative_output_tokens: int = 0


# ── session.json 读写 ──────────────────────────────────────────────────────
def load_sessions() -> dict:
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_sessions(sessions: dict) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_session(session_id: str, prompt: str, result: str,
                   input_tokens: int = 0, output_tokens: int = 0) -> None:
    """每轮对话后更新 session 记录。使用累计 token 计数。"""
    sessions = load_sessions()

    # 从 result 截取前 200 字符作为最近回复摘要
    snippet = result.strip()[:200] if result else ""

    now = datetime.now().isoformat(timespec="seconds")

    if session_id in sessions:
        entry = sessions[session_id]
        entry["last_prompt"] = prompt
        entry["last_reply_snippet"] = snippet
        entry["updated_at"] = now
        entry["turns"] = entry.get("turns", 0) + 1
        entry["total_tokens"] = entry.get("total_tokens", 0) + input_tokens + output_tokens
    else:
        sessions[session_id] = {
            "first_prompt": prompt,
            "last_prompt": prompt,
            "last_reply_snippet": snippet,
            "summary": "",
            "created_at": now,
            "updated_at": now,
            "turns": 1,
            "total_tokens": input_tokens + output_tokens,
        }

    save_sessions(sessions)


def get_latest_session() -> str | None:
    """从 session.json 中取 updated_at 最新的 session_id。"""
    sessions = load_sessions()
    if not sessions:
        return None
    return max(sessions, key=lambda sid: sessions[sid].get("updated_at", ""))


# ── 解析单行 stream-json ────────────────────────────────────────────────────
def process_line(line: str, turn: Turn) -> None:
    line = line.strip()
    if not line:
        return
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return

    t = obj.get("type", "")

    if t == "stream_event":
        event = obj.get("event", {})
        etype = event.get("type", "")

        # 尽早捕获 session_id（每个 stream_event 都可能带）
        if not turn.session_id:
            sid = obj.get("session_id", "")
            if sid:
                turn.session_id = sid

        if etype == "content_block_start":
            block = event.get("content_block", {})
            if block.get("type") == "thinking":
                print(f"\n{Color.DIM}💭 思考中…{Color.RESET}", flush=True)

        elif etype == "content_block_delta":
            delta = event.get("delta", {})
            dtype = delta.get("type", "")
            if dtype == "text_delta":
                chunk = delta.get("text", "")
                turn.text.append(chunk)
                print(f"{Color.CYAN}{chunk}{Color.RESET}", end="", flush=True)
            elif dtype == "thinking_delta":
                chunk = delta.get("thinking", "")
                turn.thinking.append(chunk)
                print(f"{Color.GRAY}{chunk}{Color.RESET}", end="", flush=True)

        elif etype == "message_delta":
            # 每个 message 结束时带 usage，逐条累加
            msg_usage = event.get("usage", {})
            turn.cumulative_input_tokens  += msg_usage.get("input_tokens", 0)
            turn.cumulative_output_tokens += msg_usage.get("output_tokens", 0)

    elif t == "assistant":
        for block in obj.get("content", []):
            if block.get("type") == "tool_use":
                turn.tool_uses.append(block)
                _print_tool_use(block)

    elif t == "tool_result":
        turn.tool_results.append(obj)
        _print_tool_result(obj)

    elif t == "result":
        turn.result     = obj.get("result", "")
        turn.session_id = obj.get("session_id", "")
        turn.usage      = obj.get("usage", {})


def _print_tool_use(t: dict) -> None:
    w = shutil.get_terminal_size().columns
    print(f"\n{Color.BLUE}{'┄' * w}{Color.RESET}")
    name = t.get("name", "?")
    inp  = t.get("input", {})
    print(f"{Color.BLUE}🔧 {Color.BOLD}{name}{Color.RESET}")
    for k, v in inp.items():
        v_str = str(v)
        if len(v_str) > 200:
            v_str = v_str[:200] + "…"
        print(f"  {Color.GRAY}{k}: {Color.RESET}{v_str}")


def _print_tool_result(r: dict) -> None:
    w       = shutil.get_terminal_size().columns
    content = r.get("content", "")
    is_err  = r.get("is_error", False)
    c       = Color.RED if is_err else Color.GREEN
    label   = "❌ 工具错误" if is_err else "✅ 工具结果"
    print(f"\n{c}{'┄' * w}{Color.RESET}")
    print(f"{c}{label}{Color.RESET}")
    snippet = str(content)[:400]
    if len(str(content)) > 400:
        snippet += f"\n{Color.GRAY}… (省略 {len(str(content)) - 400} 字符){Color.RESET}"
    print(f"{Color.GRAY}{snippet}{Color.RESET}")


# ── 调用 claude CLI ─────────────────────────────────────────────────────────
def run_claude(prompt: str, session_id: str | None = None,
               idle_timeout: int = 120) -> Turn:
    """
    session_id=None   → 新 session
    session_id="..."  → 通过 --resume 继续指定 session
    idle_timeout      → 空闲超时秒数（无输出超过此时间则终止进程）
    """
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--include-partial-messages",
    ]
    if session_id:
        cmd += ["--resume", session_id]

    w = shutil.get_terminal_size().columns
    session_label = f"  {Color.GRAY}[session: {session_id[:8]}…]{Color.RESET}" if session_id else f"  {Color.GRAY}[新对话]{Color.RESET}"
    print(f"\n{Color.YELLOW}{'═' * w}{Color.RESET}")
    print(f"{Color.YELLOW}▶ {prompt}{Color.RESET}{session_label}")
    print(f"{Color.YELLOW}{'═' * w}{Color.RESET}\n")

    turn      = Turn()
    in_stream = False
    timed_out = False

    # 空闲超时 watchdog
    last_output_time = time.monotonic()
    watchdog_stop = threading.Event()

    def _watchdog(proc, timeout):
        nonlocal timed_out
        while not watchdog_stop.is_set():
            if time.monotonic() - last_output_time > timeout:
                timed_out = True
                print(f"\n{Color.RED}⏰ 空闲超时 ({timeout}s 无输出)，正在终止 claude 进程…{Color.RESET}")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return
            watchdog_stop.wait(1)

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    ) as proc:
        # 启动 watchdog 守护线程
        wd_thread = threading.Thread(target=_watchdog, args=(proc, idle_timeout), daemon=True)
        wd_thread.start()

        for raw_line in proc.stdout:
            last_output_time = time.monotonic()
            stripped = raw_line.strip()
            if stripped:
                try:
                    obj = json.loads(stripped)
                    t   = obj.get("type", "")
                    if t == "stream_event":
                        event = obj.get("event", {})
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") in ("text_delta", "thinking_delta"):
                                in_stream = True
                    elif t in ("assistant", "tool_result", "result") and in_stream:
                        print()
                        in_stream = False
                except Exception:
                    pass
            process_line(raw_line, turn)

        # 读取 stderr
        stderr_output = proc.stderr.read() or ""

    # 停止 watchdog
    watchdog_stop.set()
    wd_thread.join(timeout=2)

    if in_stream:
        print()

    # 检查进程退出状态
    if timed_out:
        if not turn.result:
            turn.result = f"[超时] claude 进程因空闲超时 ({idle_timeout}s) 被终止"
    elif proc.returncode != 0:
        err_snippet = stderr_output.strip()[:500] if stderr_output else "(无 stderr 输出)"
        print(f"\n{Color.RED}❌ claude 进程异常退出 (code={proc.returncode}){Color.RESET}")
        print(f"{Color.RED}{err_snippet}{Color.RESET}")
        if not turn.result:
            turn.result = f"[错误] claude 进程退出码 {proc.returncode}: {err_snippet}"
    elif stderr_output and stderr_output.strip():
        warn_snippet = stderr_output.strip()[:200]
        print(f"\n{Color.YELLOW}⚠ stderr: {warn_snippet}{Color.RESET}")

    _print_summary(turn)

    # 持久化 session 记录（优先用累计 token，即使 result 消息未收到也能保存）
    if turn.session_id:
        result_text = turn.result or "".join(turn.text)
        update_session(
            turn.session_id, prompt, result_text,
            input_tokens=turn.cumulative_input_tokens or turn.usage.get("input_tokens", 0),
            output_tokens=turn.cumulative_output_tokens or turn.usage.get("output_tokens", 0),
        )

    return turn


def _print_summary(turn: Turn) -> None:
    w = shutil.get_terminal_size().columns
    print(f"\n{Color.GRAY}{'─' * w}{Color.RESET}")
    parts = []
    if turn.thinking:
        parts.append(f"thinking {len(''.join(turn.thinking))} 字符")
    if turn.tool_uses:
        names = [t.get("name", "?") for t in turn.tool_uses]
        parts.append(f"工具: {', '.join(names)}")
    # 优先使用累计 token（更准确），降级到 result.usage
    inp = turn.cumulative_input_tokens or turn.usage.get("input_tokens", 0)
    out = turn.cumulative_output_tokens or turn.usage.get("output_tokens", 0)
    if inp or out:
        parts.append(f"tokens {inp}↑ {out}↓")
    if turn.session_id:
        parts.append(f"session: {turn.session_id[:8]}…")
    if parts:
        print(f"{Color.GRAY}{' | '.join(parts)}{Color.RESET}")
    # 单次模式下输出完整 SESSION_ID 供 LLM 提取
    if turn.session_id:
        print(f"SESSION_ID: {turn.session_id}")


# ── 内置命令处理 ────────────────────────────────────────────────────────────
def handle_command(cmd: str, session_id: str | None) -> tuple[bool, str | None]:
    """
    返回 (handled, new_session_id)
    handled=True 表示已处理，不需要发给 claude
    """
    cmd_lower = cmd.strip().lower()

    if cmd_lower == "/new":
        print(f"{Color.MAGENTA}✦ 已开启新对话{Color.RESET}")
        return True, None

    if cmd_lower == "/session":
        if session_id:
            print(f"{Color.GRAY}当前 session ID: {Color.RESET}{session_id}")
        else:
            print(f"{Color.GRAY}暂无 session（还未发送任何消息）{Color.RESET}")
        return True, session_id

    if cmd_lower == "/sessions":
        sessions = load_sessions()
        if not sessions:
            print(f"{Color.GRAY}暂无保存的 session{Color.RESET}")
        else:
            print(f"\n{Color.BOLD}已保存的 session ({len(sessions)} 个):{Color.RESET}")
            for sid, info in sessions.items():
                active = " ◀" if sid == session_id else ""
                summary = info.get("summary") or info.get("last_reply_snippet", "")
                summary = summary[:60] + "…" if len(summary) > 60 else summary
                turns = info.get("turns", 0)
                updated = info.get("updated_at", "")
                print(f"  {Color.CYAN}{sid[:8]}…{Color.RESET} [{turns}轮 {updated}] {summary}{Color.GREEN}{active}{Color.RESET}")
            print()
        return True, session_id

    if cmd_lower == "/help":
        print(
            f"\n{Color.BOLD}内置命令:{Color.RESET}\n"
            f"  {Color.CYAN}/new{Color.RESET}       开启新对话（丢弃当前 session）\n"
            f"  {Color.CYAN}/session{Color.RESET}   显示当前 session ID\n"
            f"  {Color.CYAN}/sessions{Color.RESET}  列出所有已保存的 session\n"
            f"  {Color.CYAN}/help{Color.RESET}      显示此帮助\n"
            f"  {Color.CYAN}exit / q{Color.RESET}   退出\n"
        )
        return True, session_id

    return False, session_id


# ── 参数解析 ────────────────────────────────────────────────────────────────
def parse_args() -> tuple[str | None, str | None, bool, int]:
    """
    解析命令行参数。

    返回 (resume_session_id, prompt, force_new, idle_timeout)
    - 都为 None 且 force_new=False → 交互模式（自动恢复最新 session）
    - prompt 有值 → 单次模式
    - force_new=True → 强制新建 session
    - idle_timeout → 空闲超时秒数（默认 120）
    """
    args = sys.argv[1:]
    resume_id = None
    force_new = False
    idle_timeout = 120
    prompt_parts = []

    i = 0
    while i < len(args):
        if args[i] in ("--resume", "-r") and i + 1 < len(args):
            resume_id = args[i + 1]
            i += 2
        elif args[i] in ("--new", "-n"):
            force_new = True
            i += 1
        elif args[i] == "--idle-timeout" and i + 1 < len(args):
            try:
                idle_timeout = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            prompt_parts.append(args[i])
            i += 1

    prompt = " ".join(prompt_parts) if prompt_parts else None
    return resume_id, prompt, force_new, idle_timeout


# ── 主入口 ──────────────────────────────────────────────────────────────────
def main() -> None:
    resume_id, prompt, force_new, idle_timeout = parse_args()

    if prompt:
        # 单次问答模式
        if force_new:
            session_id = None
        elif resume_id:
            session_id = resume_id
        else:
            # 默认继续上次 session
            session_id = get_latest_session()
        run_claude(prompt, session_id=session_id, idle_timeout=idle_timeout)
        return

    # 交互模式
    w = shutil.get_terminal_size().columns
    print(f"{Color.BOLD}Claude Chat{Color.RESET}  "
          f"{Color.GRAY}/new 新对话  /sessions 列表  /help 帮助  exit 退出{Color.RESET}")
    print(f"{Color.GRAY}{'─' * w}{Color.RESET}\n")

    # 自动恢复：--resume 优先，否则取最新 session（--new 则跳过）
    if force_new:
        session_id = None
    elif resume_id:
        session_id = resume_id
    else:
        session_id = get_latest_session()

    if session_id:
        sessions = load_sessions()
        info = sessions.get(session_id, {})
        summary = info.get("summary") or info.get("first_prompt", "")
        print(f"{Color.GREEN}↻ 已恢复上次对话: {Color.RESET}{summary}")
        print(f"{Color.GRAY}  session: {session_id[:8]}… | {info.get('turns', 0)} 轮{Color.RESET}\n")

    turn_num = 0

    while True:
        if session_id:
            hint = f"{Color.GRAY}[#{turn_num} {session_id[:6]}…]{Color.RESET} "
        else:
            hint = f"{Color.GRAY}[新]{Color.RESET} "

        try:
            user_input = input(f"{Color.BOLD}你{Color.RESET} {hint}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q", "退出"):
            print("再见！")
            break

        # 内置命令
        if user_input.startswith("/"):
            handled, session_id = handle_command(user_input, session_id)
            if handled:
                continue

        # 发送给 claude
        turn = run_claude(user_input, session_id=session_id, idle_timeout=idle_timeout)

        if turn.session_id:
            session_id = turn.session_id
        turn_num += 1


if __name__ == "__main__":
    main()
