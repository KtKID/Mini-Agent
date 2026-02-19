# Agent Team v1.0 - 多智能体聊天室

## 1. 简介

Agent Team 是一个支持多个 AI Agent 在同一话题下协同讨论的模块。

### 核心特性

- **多模型支持** - 支持 Anthropic、OpenAI、DeepSeek、智谱AI、MiniMax、Ollama、LM Studio 等
- **共享内存** - 所有 Agent 共享同一套对话记忆，每个 Agent 都能看到完整上下文
- **异步讨论** - 所有 Agent 并发响应，提高讨论效率
- **灵活配置** - 每个 Agent 可配置不同的模型、API 端点、性格特征

## 2. 快速开始

### 运行示例脚本

```bash
# 查看配置的 Agent 列表
python run_discussion.py --list-agents

# 运行讨论
python run_discussion.py --topic "如何设计高并发系统?" --rounds 2
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--topic` | 讨论话题 | 见脚本配置 |
| `--rounds` | 讨论回合数 | 1 |
| `--config` | 配置文件路径 | mini_agent/config/config.yaml |
| `--list-agents` | 列出预配置的 Agent | - |

## 3. 配置

### 3.1 config.yaml 配置

在 `mini_agent/config/config.yaml` 中配置 providers：

```yaml
agent_team:
  providers:
    # Anthropic (Claude)
    anthropic:
      enabled: true
      api_url: "https://api.anthropic.com"
      # api_key: 从环境变量 ANTHROPIC_API_KEY 读取

    # OpenAI (GPT)
    openai:
      enabled: true
      api_url: "https://api.openai.com/v1"

    # DeepSeek
    deepseek:
      enabled: true
      api_url: "https://api.deepseek.com/v1"

    # 智谱 AI (BigModel)
    bigmodel:
      enabled: false
      api_url: "https://open.bigmodel.cn/api/paas/v4"

    # MiniMax
    minimax:
      enabled: false
      api_url: "https://api.minimax.chat/v1"

    # Ollama (本地模型)
    ollama:
      enabled: false
      api_url: "http://localhost:11434/v1"

    # LM Studio (本地模型)
    lmstudio:
      enabled: false
      api_url: "http://127.0.0.1:1234/v1"

    # 自定义 API
    custom:
      enabled: false
      api_url: "http://localhost:8000/v1"
```

### 3.2 环境变量

| Provider | 环境变量 |
|----------|----------|
| anthropic | `ANTHROPIC_API_KEY` |
| openai | `OPENAI_API_KEY` |
| deepseek | `DEEPSEEK_API_KEY` |
| bigmodel | `BIGMODEL_API_KEY` |
| minimax | `MINIMAX_API_KEY` |
| custom | `CUSTOM_API_KEY` |

### 3.3 支持的模型

| Provider | 示例模型 |
|----------|----------|
| anthropic | claude-sonnet-4-20250514, claude-3-5-sonnet-20241022 |
| openai | gpt-4, gpt-4-turbo, gpt-3.5-turbo |
| deepseek | deepseek-chat, deepseek-coder |
| bigmodel | glm-5, glm-4-flash |
| minimax | abab6.5s-chat, MiniMax-M2.5 |
| ollama | qwen2.5, llama3, mistral |
| lmstudio | glm-4.7-flash (本地模型) |

## 4. 使用方法

### 4.1 Python API

```python
import asyncio
from mini_agent.agent_team import AgentTeam, load_providers_from_config

# 从配置文件加载 providers
providers_config = load_providers_from_config()

# 创建聊天室
team = AgentTeam(
    name="技术评审",
    max_agents=10,
    timeout=60.0,
    providers_config=providers_config
)

# 添加 Agent (使用 provider_id)
team.add_agent(
    name="Claude专家",
    provider_id="anthropic",
    model_name="claude-sonnet-4-20250514",
    personality_name="专业冷静",
    system_prompt="你是一个资深技术专家。回答问题时保持客观理性。"
)

team.add_agent(
    name="GPT助手",
    provider_id="openai",
    model_name="gpt-4",
    personality_name="热情友好",
    system_prompt="你是一个热情友好的助手。"
)

# 发起讨论
async def main():
    results = await team.discuss("如何优化数据库查询性能?")

    # 查看结果
    for r in results:
        if r.success:
            print(f"\n=== {r.agent_name} ===")
            print(r.content)
        else:
            print(f"\n=== {r.agent_name} 错误 ===")
            print(r.error)

asyncio.run(main())
```

### 4.2 添加/移除 Agent

```python
# 添加 Agent
agent = team.add_agent(
    name="新Agent",
    provider_id="deepseek",
    model_name="deepseek-chat",
    system_prompt="你的系统提示词"
)

# 移除 Agent
team.remove_agent(agent.id)

# 获取 Agent
agent = team.get_agent(agent_id)

# 列出所有 Agent
agents = team.list_agents()
```

### 4.3 查看共享内存

```python
# 消息数量
print(f"消息数: {team.chatroom.memory.count()}")

# 获取所有消息
messages = team.chatroom.memory.get_messages()

# 获取给 Agent 的消息格式
agent_messages = team.chatroom.memory.get_messages_for_agent()

# 清空内存
team.chatroom.memory.clear()
```

## 5. 代码示例

### 5.1 自定义 Agent 配置

```python
# 创建带自定义性格的 Agent
team.add_agent(
    name="技术顾问",
    provider_id="anthropic",
    model_name="claude-sonnet-4-20250514",
    personality_name="技术顾问",
    system_prompt="""你是一个资深技术顾问。回答问题时:
- 保持客观理性，用数据说话
- 给出具体可执行的建议
- 遇到不确定的问题明确说明""",
    response_style="简洁专业"
)
```

### 5.2 多回合讨论

```python
async def multi_round_discussion(team, topic, rounds=3):
    for round_num in range(1, rounds + 1):
        print(f"\n=== 第 {round_num} 轮 ===")
        results = await team.discuss(topic)

        for r in results:
            if r.success:
                print(f"{r.agent_name}: {r.content[:100]}...")

        print(f"\n共享记忆: {team.chatroom.memory.count()} 条消息")

asyncio.run(multi_round_discussion(team, "分布式系统设计", rounds=3))
```

## 6. 架构设计

### 6.1 核心组件

```
AgentTeam
├── Chatroom (聊天室)
│   └── Memory (共享内存)
│       └── Message (消息)
├── Agent (智能体)
│   ├── AgentConfig (配置)
│   └── Personality (性格)
└── Provider 配置
    └── ProviderConfig
```

### 6.2 组件说明

| 组件 | 说明 |
|------|------|
| AgentTeam | 主入口，管理聊天室和 Agent 列表 |
| Chatroom | 聊天室，包含共享 Memory |
| Memory | 消息存储，所有 Agent 共享 |
| Agent | 单个 AI Agent，包含模型配置和性格 |
| Personality | Agent 性格配置（名称、提示词、回复风格） |
| ProviderConfig | 模型提供商配置（API URL、Key） |

### 6.3 数据流

1. 用户发起讨论 (`team.discuss(topic)`)
2. 话题作为用户消息存入 Memory
3. 所有活跃 Agent 并发获取 Memory 中的消息
4. 每个 Agent 调用对应的 LLM 生成响应
5. 响应存入 Memory
6. 返回所有 Agent 的响应结果

## 7. 运行测试

```bash
# 运行单元测试
uv run python tests/agent_team/test_agent_team.py
```

测试结果：
```
==================================================
Agent Team 自动化测试
==================================================
测试结果: 32 通过, 0 失败
==================================================
```

## 8. 常见问题

### Q1: 如何添加新的模型提供商?

在以下文件中添加配置：

1. `providers.py` - 添加 ProviderConfig 和环境变量映射
2. `__init__.py` - 添加 provider_map 映射

### Q2: 本地模型连接失败?

1. 确认 Ollama/LM Studio 已启动
2. 检查端口配置是否正确
3. 模型是否已加载

### Q3: API 请求超时?

调整 `AgentTeam` 的 `timeout` 参数：

```python
team = AgentTeam(name="讨论", timeout=120.0)  # 120秒超时
```

### Q4: 如何禁用某个 Agent?

```python
agent = team.get_agent(agent_id)
agent.deactivate()  # 停用

agent.activate()   # 重新激活
```

## 9. 更新日志

### v1.0 (2026-02-19)

- 初始版本发布
- 支持多模型提供商 (Anthropic, OpenAI, DeepSeek, BigModel, MiniMax, Ollama, LM Studio, Custom)
- 共享 Memory 功能
- 异步并发讨论
- 灵活的性格配置
- 完整的单元测试覆盖
