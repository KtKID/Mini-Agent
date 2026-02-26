# Review: 捕获 stderr 错误反馈 (29210c45)

## 改动概述

将 `subprocess.Popen` 的 `stderr` 从 `DEVNULL` 改为 `PIPE`，新增进程退出码和 stderr 内容的分级处理。

## 潜在问题

### 1. 死锁风险（中等）

当前逻辑：先遍历完 stdout，再 `proc.stderr.read()`。若 claude 向 stderr 大量写入（超过 OS pipe buffer ~64KB），stderr pipe 满 → 子进程阻塞 → stdout 也停 → 主线程阻塞 → **死锁**。

### 2. 超时场景遗漏 stderr

`timed_out=True` 时直接走 timeout 分支，跳过了 stderr 展示。超时场景下 stderr 可能含有用信息。

### 3. watchdog 终止后 stderr 可能已关闭

watchdog 线程 terminate/kill 进程后，`proc.stderr.read()` 可能抛异常，建议加 `try/except`。

## 改进方案

### 方案：异步线程读取 stderr

用独立守护线程持续 drain stderr，彻底避免 pipe buffer 满导致的死锁。

```python
# ---- 在 run_claude() 函数中 ----

# 1. 异步收集 stderr
stderr_chunks: list[str] = []

def _drain_stderr(stream):
    """守护线程：持续读取 stderr，防止 pipe buffer 满导致死锁。"""
    try:
        for line in stream:
            stderr_chunks.append(line)
    except (ValueError, OSError):
        pass  # 进程被 kill 后 stream 可能已关闭

# 2. 在 Popen 启动后、stdout 循环之前，启动 stderr 读取线程
stderr_thread = threading.Thread(target=_drain_stderr, args=(proc.stderr,), daemon=True)
stderr_thread.start()

# 3. stdout 循环结束后，等待 stderr 线程完成
stderr_thread.join(timeout=5)
stderr_output = "".join(stderr_chunks)

# 4. 超时分支也输出 stderr（补全遗漏）
if timed_out:
    if not turn.result:
        turn.result = f"[超时] claude 进程因空闲超时 ({idle_timeout}s) 被终止"
    if stderr_output and stderr_output.strip():
        warn_snippet = stderr_output.strip()[:300]
        print(f"\n{Color.YELLOW}⚠ stderr (超时): {warn_snippet}{Color.RESET}")
elif proc.returncode != 0:
    # ... 现有逻辑不变 ...
```

### 改动点汇总

| 位置 | 改动 | 目的 |
|------|------|------|
| stdout 循环前 | 启动 `_drain_stderr` 线程 | 防死锁 |
| stdout 循环后 | `stderr_thread.join(5)` | 安全收集 |
| `_drain_stderr` | `try/except ValueError/OSError` | 防进程被 kill 后异常 |
| `timed_out` 分支 | 补充 stderr 输出 | 超时也可见错误 |
