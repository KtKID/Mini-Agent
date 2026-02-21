# 飞书讨论模式集成开发计划

## Context

用户通过飞书与主 mini-agent 对话，需要支持关键词触发讨论模式：用户发送"讨论 {话题}"后，列出 `agents.yaml` 中可用的 Agent 供选择，用户选择后 Agent 按 DEBATE 模式顺序发言，每个发言通过飞书逐条发送给用户。用户可追加观点触发下一轮，或发送"讨论结束"退出。

**当前问题**：
1. agents.yaml 中所有 agent 被全部加载，无法按需选择
2. 飞书 callback 签名 `(open_id, content) -> str` 只能返回单条消息，无法逐条发送
3. 没有讨论状态管理（状态机），无法跟踪用户处于选择/讨论哪个阶段

## 实施步骤

### Step 1: 扩展 AgentConfigLoader — 添加格式化列表方法

**修改 `mini_agent/agents/__init__.py`**

在 `AgentConfigLoader` 中添加 `format_agent_list()` 方法，返回带编号的 agent 列表文本：
```
1. deepseek专家 (deepseek-chat) — 专业冷静
2. 智谱助手 (glm-5) — 中文专家
3. MiniMax专家 (MiniMax-M2.5) — 全能助手
4. lmstudio (glm-4.7-flash) — 本地助手
```
该方法复用已有的 `load_agents()` + `resolve_personality()`。

### Step 2: 新建 DiscussionHandler — 讨论状态机

**新建 `mini_agent/agent_team/discussion_handler.py`**

```
DiscussionState(Enum):
    SELECTING   — 等待用户选择 Agent
    DISCUSSING  — 讨论进行中

UserDiscussionSession(dataclass):
    open_id: str
    topic: str
    state: DiscussionState
    team: AgentTeam          — 该话题的独立 AgentTeam（含独立 Memory）
    round_num: int = 0
    agent_names: list[str]   — 已选 Agent 名称列表

DiscussionHandler(class):
    __init__(providers_config, loader)
        — providers_config: 从 config.yaml 加载的 ProvidersConfig（用于创建 AgentTeam）
        — loader: AgentConfigLoader（已加载 templates 和 agent_defs）

    is_active(open_id) -> bool
        — 检查用户是否有活跃讨论 session

    async handle_message(open_id, content, send_fn) -> None
        — 总路由，根据当前状态分派到下面的方法
        — send_fn: Callable[[str], Awaitable[None]]，发送飞书消息

    async _start_discussion(open_id, topic, send_fn)
        — 创建 UserDiscussionSession（state=SELECTING）
        — 发送话题确认 + agent 列表 + 选择提示

    async _select_agents(open_id, content, send_fn)
        — 解析用户输入（"1,3" 或 "全部"）
        — 验证编号有效性，无效则提示重新输入
        — 创建 AgentTeam，添加选中的 agent
        — state → DISCUSSING
        — 运行第 1 轮讨论

    async _handle_discussing(open_id, content, send_fn)
        — "讨论结束" → _end_discussion()
        — "继续" → _run_round(不添加新消息)
        — 其他文本 → _run_round(文本作为用户观点加入 Memory)

    async _run_round(session, send_fn, user_message=None)
        — round_num += 1
        — 如果有 user_message，加入 Memory
        — 遍历 team 中的 active agents，逐个调用 generate_response
        — 每个 agent 发言后立即 send_fn 发送飞书消息
        — 发言写入 Memory（下一个 agent 能看到）
        — 最后发送轮次提示

    async _end_discussion(open_id, send_fn)
        — 发送总结（话题、参与者、轮次、消息数）
        — 清理 session
```

**关键设计：`_run_round` 不使用 `team.discuss()`，而是直接遍历 agent 调用 `generate_response`**。原因：`discuss()` 是批量返回所有结果，但飞书场景需要每个 agent 发言后**立即**发送消息给用户，实现"逐条推送"的体验。直接复用 AgentTeam 的 Memory 和 Agent 对象，只是跳过 discuss 的批量返回逻辑。

### Step 3: 扩展飞书 callback 签名 — 支持多消息发送

**修改 `mini_agent/skills/feishu_skill/__init__.py`**

当前 callback 签名：
```python
_agent_callback: Callable[[str, str], Awaitable[str]]
# (open_id, content) -> response
```

改为：
```python
_agent_callback: Callable[[str, str, Callable], Awaitable[Optional[str]]]
# (open_id, content, send_fn) -> Optional[response]
```

修改 `_handle_message_event` 方法（第 240-272 行）：
```python
async def _handle_message_event(self, event_data: dict) -> None:
    open_id = event_data["open_id"]
    message_id = event_data["message_id"]
    content = event_data["content"]

    session = self._session_manager.get_or_create(open_id)
    session.message_count += 1

    if self._agent_callback:
        try:
            await self.create_reaction(message_id, "LOVE")

            # 创建 send_fn 供 callback 主动发送多条消息
            async def send_fn(text: str) -> None:
                await self.send_text(open_id, text)

            response = await self._agent_callback(open_id, content, send_fn)

            # 如果 callback 返回了文本，发送它（普通模式）
            # 如果返回 None，说明 callback 已自行发送消息（讨论模式）
            if response:
                await self.send_text(open_id, response)
        except Exception as e:
            logger.error(f"FeishuSkill: [PROCESS_ERROR] {e}")
            await self.send_text(open_id, "抱歉，处理您的消息时发生错误。")
```

### Step 4: 修改 cli.py — 接入 DiscussionHandler

**修改 `mini_agent/cli.py` 第 638-662 行的 `feishu_message_handler`**

```python
# 在 feishu_skill 初始化块中（约第 636 行后）:

# 创建 DiscussionHandler
from mini_agent.agent_team.discussion_handler import DiscussionHandler
from mini_agent.agents import AgentConfigLoader
from mini_agent.agent_team import load_agent_team_config

team_config = load_agent_team_config()
loader = AgentConfigLoader()
loader.load_personality_templates()

discussion_handler = DiscussionHandler(
    providers_config=team_config.providers_config,
    loader=loader,
    timeout=team_config.timeout,
)

async def feishu_message_handler(open_id: str, message: str, send_fn) -> Optional[str]:
    # 讨论模式判断
    if discussion_handler.is_active(open_id) or message.startswith("讨论 "):
        await discussion_handler.handle_message(open_id, message, send_fn)
        return None  # DiscussionHandler 已通过 send_fn 发送消息

    # 普通模式 — 原有逻辑
    session_agent = Agent(
        llm_client=LLMClient(...),
        system_prompt=system_prompt,
        tools=tools,
        max_steps=config.agent.max_steps,
        workspace_dir=str(workspace_dir),
    )
    session_agent.add_user_message(message)
    await session_agent.run()
    for msg in reversed(session_agent.messages):
        if msg.role == "assistant" and msg.content:
            return msg.content
    return "抱歉，我无法生成回复。"
```

## 修改文件清单

| 文件 | 操作 | 关键变更 |
|------|------|---------|
| `mini_agent/agent_team/discussion_handler.py` | **新建** | DiscussionHandler 状态机 + UserDiscussionSession |
| `mini_agent/agents/__init__.py` | 修改 | 添加 `format_agent_list()` 方法 |
| `mini_agent/skills/feishu_skill/__init__.py` | 修改 | callback 签名加 `send_fn`，`_handle_message_event` 支持 None 返回 |
| `mini_agent/cli.py` | 修改 | 创建 DiscussionHandler，更新 `feishu_message_handler` 路由逻辑 |

## 用户交互流程

```
用户: "讨论 如何设计分布式系统"
Bot:  话题：如何设计分布式系统
      可用 Agent:
      1. deepseek专家 (deepseek-chat) — 专业冷静
      2. 智谱助手 (glm-5) — 中文专家
      3. MiniMax专家 (MiniMax-M2.5) — 全能助手
      4. lmstudio (glm-4.7-flash) — 本地助手
      请输入编号（逗号分隔），或输入"全部"

用户: "1,3"
Bot:  参与者: deepseek专家, MiniMax专家 — 讨论开始
Bot:  【第 1 轮 · deepseek专家】...    ← 逐条发送
Bot:  【第 1 轮 · MiniMax专家】...    ← 逐条发送
Bot:  第 1 轮结束 | 发消息继续 | "继续"下一轮 | "讨论结束"

用户: "我觉得应该用微服务"        ← 作为新观点加入
Bot:  【第 2 轮 · deepseek专家】...
Bot:  【第 2 轮 · MiniMax专家】...
Bot:  第 2 轮结束 | ...

用户: "讨论结束"
Bot:  讨论结束 | 话题: ... | 参与: ... | 2 轮 | 7 条消息
```

## 验证方式

1. 启动 mini-agent（确保 feishu enabled），通过飞书发送 "讨论 测试话题"
2. 确认收到 agent 列表，输入编号选择
3. 确认每个 agent 发言逐条推送到飞书
4. 发送文字确认触发下一轮，所有 agent 能看到用户观点
5. 发送"继续"确认触发下一轮但不加新消息
6. 发送"讨论结束"确认收到总结并回到普通模式
7. 发送普通消息确认回到主 agent 对话模式
