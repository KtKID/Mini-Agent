# Review: 空闲超时控制 + BashTool timeout 指导 (0300a60e)

| 项 | 详情 |
|---|---|
| **提交** | `0300a60e0f3da5ca6d34737229266c1d1238770d` |
| **日期** | 2026-02-26 14:07:54 +0800 |
| **改动** | `SKILL.md` (+16), `claude_chat.py` (+59, -8) |

---

## 改动概述

1. **watchdog 空闲超时机制**：新增守护线程监控 stdout 输出间隔，超时则 terminate → kill 子进程
2. **`--idle-timeout` CLI 参数**：默认 120s，可自定义
3. **SKILL.md 文档补充**：指导调用方设置 `BashTool timeout=300`，并说明 `--idle-timeout` 用法

## ✅ 优点

- **解决实际痛点**：编程任务耗时长，之前无超时保护会导致进程挂死
- **watchdog 设计合理**：守护线程 + `threading.Event` + 1s 轮询，开销小且响应及时
- **优雅退出**：先 `terminate()`，等 5s 后若未退出再 `kill()`
- **文档同步更新**：SKILL.md 同时更新了调用指导，减少使用者踩坑

## ⚠️ 潜在问题

### 1. watchdog 线程访问 `last_output_time` 无同步保护（低风险）

`last_output_time` 在主线程写、watchdog 线程读，Python GIL 下 float 赋值是原子的，实际安全。但从代码规范角度，可考虑用 `threading.Lock` 或 `_watchdog_stop` event 的 timeout 替代轮询。

### 2. `_watchdog` 中 nonlocal timed_out 同样依赖 GIL

与上同理，bool 赋值在 CPython 下安全，但不严格线程安全。

### 3. watchdog stop 时序

`watchdog_stop.set()` 在 `with` 块外执行。若进程被 watchdog 终止，`with` 块正常退出后才 `set()`。由于 watchdog 已 `return`，`join(2)` 能正常回收。逻辑正确但流程略隐晦。

### 4. `--idle-timeout` 参数解析无范围校验

用户传 `--idle-timeout 0` 或负数时会立即触发超时。建议加最小值校验。

## 💡 改进建议

```python
# 1. idle_timeout 合法性校验
elif args[i] == "--idle-timeout" and i + 1 < len(args):
    try:
        val = int(args[i + 1])
        idle_timeout = max(30, min(val, 600))  # 限制 30~600s
    except ValueError:
        pass
    i += 2

# 2. 可选：用 threading.Lock 保护 last_output_time（严格线程安全）
output_lock = threading.Lock()

# 写
with output_lock:
    last_output_time = time.monotonic()

# 读
with output_lock:
    elapsed = time.monotonic() - last_output_time
```

## 总结

实用的防挂死保护，设计简洁有效。主要建议加 timeout 参数范围校验。**👍 Good**
