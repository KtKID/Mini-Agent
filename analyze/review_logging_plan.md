# 日志方案与测试用例的验证及优化建议

根据对项目中 `claude_chat.py` 及其子模块（主要涉及 `process_line`、`run_claude`、`handle_command` 及 `session_utils.py`）的真实运行逻辑进行校验，以下是针对 `analyze/plan_logging_system.md` 的验证与优化建议。

## 一、测试用例数据集的正确性验证：完全匹配 ✅

你在 `plan_logging_system.md` 第九部分规划的“真实据格式验证 session 隔离”的测试用例数据是**完全准确**的，原因如下：

1. **飞书真实 ID 原样保留**：
   - 飞书私聊（`ou_abc123def456ghi789`）和群聊（`oc_groupchat123456789`）的 ID 由于仅包含小写字母、数字和下划线，被传入 `claude_chat.py` 后调用 `session_utils._safe_id`（执行正则 `re.sub(r'[^a-zA-Z0-9_\-]', '_', user_id)`）。
   - 正则只会替换特殊字符，因此 `ou_` 和 `oc_` 会被原样保留，从而真实生成 `session_ou_abc123...json` 文件。此数据构造行为与生产完全一致。

2. **累积 Token 的持久化逻辑匹配**：
   - 测试用例假设 `run_claude` 结束时使用累积的输入/输出 Tokens。根据代码，`process_line` 中对 `message_delta` 的累加（`turn.cumulative_input_tokens`）确实通过了最终 `update_session` 传参：`input_tokens=turn.cumulative_input_tokens or ...`。
   - `update_session` 本身也正确实现了增量叠加：`entry["total_tokens"] = entry.get("total_tokens", 0) + input_tokens + output_tokens`。测试中的数据闭环是正确的。

3. **Bash 命令拼装格式正确**：
   - `run_claude` 中的 `--resume` 构建机制，正如日志方案第七部分的示例一样，会在有 `resume_id` 时把参数正确放入 `cmd`。

---

## 二、日志方案（plan_logging_system.md）的优化点 (⭐️⭐️⭐️)

尽管现有方案已能打通飞书和 Coding 链路，但针对真实交互的代码细节，还有以下关键优化点需要补充到方案中：

### 1. 补充 Tool Use（工具调用）的过程日志 (P0)

**问题**：当前的方案仅记录了 `run_claude` 整体进程的开始（`[RUN]`）与结束（`[DONE]`）。但在 Coding 过程中，绝大部分时间花费在让大模型自循环调用工具上。如果在某次 bash 调用中卡住，现有的 `[DONE]` 根本无从知道是大模型挂了还是工具执行挂了。

**优化方案**：
在 `claude_chat.py` 的 `process_line()` 函数中，对解析到的工具调用（`assistant / tool_use`）和工具返回值（`tool_result`）都加上 DEBUG/INFO 级别的局部日志：
```python
# process_line 中的新增日志：
elif t == "assistant":
    for block in obj.get("content", []):
        if block.get("type") == "tool_use":
            turn.tool_uses.append(block)
            _print_tool_use(block)
            _log.info(f"[TOOL_USE] session_id={turn.session_id} tool={block.get('name')} input_len={len(str(block.get('input')))}")

elif t == "tool_result":
    turn.tool_results.append(obj)
    _print_tool_result(obj)
    _log.info(f"[TOOL_RES] session_id={turn.session_id} is_error={obj.get('is_error')} output_len={len(str(obj.get('content')))}")
```
*这极大地帮助后续「用真实数据排查由于循环过长产生的幻觉或超时」*。

### 2. 精确化空闲超时 (Watchdog) 的日志位置 (P1)

**问题**：设计里提到由外部主线程 `run_claude` 判断超时（`C5 | 超时分支`），但实际上 Watchdog 是一个异步线程，它一旦超时会强杀 `proc.terminate()` 进程，主循环的读取会由于子进程被杀而抛错结束。

**优化方案**：
不应仅在 `run_claude` 阻塞跳出后输出超时，应**同时在 Watchdog 线程的执行体内**打印日志：
```python
# 在 run_claude._watchdog 内：
if time.monotonic() - last_output_time > timeout:
    timed_out = True
    _log.warning(f"[TIMEOUT_CRITICAL] watchdog terminated proc, idle>{timeout}s")
    # ... proc.terminate()
```

### 3. BashTool 日志不需要受环境变量限制 (P2)

**问题**：设计在 `Layer 2: bash_tool.py` 中写到通过 `os.environ.get("BASH_LOG_ENABLED") == "1"` 提取日志开关。
但这并不必要。`bash_tool.py` 运行在 `mini_agent` 的父进程（跟 `cli.py` 在同一个 Python 进程）里，是可以直接注入此开关，或者通过向 `BashTool` 构造函数传递实例变量控制。
当然，保持读取环境变量是个解耦的好办法，但需要注意：不要因为系统环境变量的覆盖导致串台。

### 4. 解决 `summarize_sessions.py` 被定时任务独立调用的场景 (P3)

**问题**：`session_utils.py` 里使用了 `mini_agent.coding` logger 记录着 `[LOAD]` 和 `[SAVE]` 行为。它也是被 `summarize_sessions.py` 共用的模块。如果将来将总结功能独立成 Cron Job 执行，此时大概率不会有 `CODING_LOG_ENABLED` 等环境变量。
**优化方案**：
在 `session_utils.py` 的顶部做一次优雅降级判断，如果获取 logger 没有挂载 handler，则丢弃日志或只给一个 NullHandler：
```python
import logging
_log = logging.getLogger("mini_agent.coding")
if not _log.handlers:
    _log.addHandler(logging.NullHandler())
```

---

## 结论

1. **测试用例集的正确性毫无问题**，完全依照当前工程底层飞书 ID 的字符串特性与 session_utils 中的正则匹配生成，可直接实施用于下一步代码编写。
2. **需要针对上述 4 点（重点是 Tool Use 和 Watchdog 线程的日志定位）更新至你的日志架构文档中。**
