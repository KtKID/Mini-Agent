# Quickstart: Agent Team 多智能体聊天室

## 1. 快速开始

### 1.1 安装

确保已安装 Mini-Agent 依赖：

```bash
uv sync
```

### 1.2 配置 Agent

在 `config.yaml` 中添加 Agent Team 配置：

```yaml
agent_team:
  enabled: true

  # Agent 配置列表
  agents:
    - name: "Claude专家"
      model_provider: anthropic
      model_name: "claude-sonnet-4-20250514"
      personality:
        name: "专业冷静"
        system_prompt: "你是一个专业的技术顾问，回答问题冷静客观。"

    - name: "GPT助手"
      model_provider: openai
      model_name: "gpt-4"
      api_url: "https://api.openai.com/v1"
      personality:
        name: "热情积极"
        system_prompt: "你是一个热情友好的助手，喜欢用生动的例子解释问题。"
```

### 1.3 使用聊天室

```python
from mini_agent.agent_team import AgentTeam

# 创建聊天室
team = AgentTeam(name="技术评审")

# 添加 Agent
team.add_agent(
    name="Claude专家",
    model_provider="anthropic",
    model_name="claude-sonnet-4-20250514",
    personality={"name": "专业冷静", "system_prompt": "..."}
)

# 发起讨论
response = await team.discuss("如何优化数据库查询性能？")

# 获取所有 Agent 的响应
for agent_response in response.responses:
    print(f"{agent_response.agent_name}: {agent_response.content}")
```

---

## 2. 配置说明

### 2.1 ModelProvider

| 值 | API |
|----|-----|
| `openai` | OpenAI API |
| `anthropic` | Anthropic API |
| `custom` | 自定义兼容 API |

### 2.2 自定义 API

使用自定义 API 端点：

```yaml
- name: "本地模型"
  model_provider: custom
  model_name: "qwen2.5"
  api_url: "http://localhost:8000/v1"
  api_key: "your-api-key"  # 可选
  personality:
    name: "本地助手"
    system_prompt: "你是一个本地部署的AI助手。"
```

---

## 3. 性格配置示例

### 3.1 专业冷静型

```yaml
personality:
  name: "专业冷静"
  system_prompt: |
    你是一个资深技术专家。回答问题时：
    - 保持客观理性，用数据说话
    - 给出具体可执行的建议
    - 遇到不确定的问题明确说明
  response_style: "简洁、专业、用技术术语"
```

### 3.2 热情友好型

```yaml
personality:
  name: "热情友好"
  system_prompt: |
    你是一个热情友好的助手。回答问题时：
    - 使用生动的例子帮助理解
    - 适当使用表情增加亲切感
    - 鼓励用户继续提问
  response_style: "活泼、易懂、亲切"
```

### 3.3 严谨分析型

```yaml
personality:
  name: "严谨分析"
  system_prompt: |
    你是一个严谨的分析师。回答问题时：
    - 先分析问题，再给出答案
    - 列出优缺点供用户选择
    - 考虑边界情况和异常情况
  response_style: "条理清晰、全面分析"
```

---

## 4. 常见问题

### Q1: 如何添加 Agent 到聊天室？

```python
team.add_agent(config_dict)
```

### Q2: 如何查看聊天室历史？

```python
messages = team.chatroom.memory.get_messages()
```

### Q3: 如何清空记忆？

```python
team.chatroom.memory.clear()
```

### Q4: Agent 调用失败怎么办？

每个 Agent 的错误会被隔离记录，不影响其他 Agent 的响应。

---

## 5. 示例场景

### 5.1 技术方案评审

```python
team = AgentTeam(name="技术评审")

# 添加不同性格的 Agent
team.add_agent(
    name="架构师",
    model_provider="anthropic",
    model_name="claude-sonnet-4-20250514",
    personality={"name": "架构视角", "system_prompt": "你从系统架构角度分析问题，关注可扩展性、可靠性。"}
)

team.add_agent(
    name="安全专家",
    model_provider="openai",
    model_name="gpt-4",
    personality={"name": "安全视角", "system_prompt": "你从安全角度分析问题，关注潜在风险和防护措施。"}
)

# 发起评审
result = await team.discuss("我们计划使用微服务架构，请给出建议")
```

---

## 6. API 参考

| 方法 | 说明 |
|------|------|
| `AgentTeam(name)` | 创建聊天室 |
| `team.add_agent(config)` | 添加 Agent |
| `team.remove_agent(agent_id)` | 移除 Agent |
| `await team.discuss(topic)` | 发起讨论 |
| `team.chatroom.memory.get_messages()` | 获取历史 |
| `team.chatroom.memory.clear()` | 清空记忆 |
