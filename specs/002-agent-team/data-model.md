# Data Model: Agent Team 多智能体聊天室

## 1. 核心实体

### 1.1 Chatroom (聊天室)

聊天室是多 Agent 讨论的共享空间。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 唯一标识，UUID |
| name | string | 是 | 聊天室名称 |
| created_at | timestamp | 是 | 创建时间 |
| members | list[Agent] | 是 | 成员 Agent 列表 |
| memory | Memory | 是 | 共享记忆 |
| max_members | int | 否 | 最大成员数，默认 10 |

### 1.2 Agent (智能体)

每个 Agent 有独立的模型配置和性格。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 唯一标识 |
| name | string | 是 | Agent 名称 |
| model_provider | ModelProvider | 是 | 模型提供商 |
| model_name | string | 是 | 模型名称 |
| api_url | string | 否 | 自定义 API 端点 |
| api_key | string | 否 | API 密钥 |
| personality | Personality | 是 | 性格配置 |
| is_active | bool | 是 | 是否活跃 |

### 1.3 ModelProvider (模型提供商)

支持的 AI 模型类型。

| 值 | 说明 |
|----|------|
| openai | OpenAI API |
| anthropic | Anthropic API |
| custom | 自定义 API |

### 1.4 Personality (性格配置)

Agent 的系统提示词和行为特征。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 性格名称，如"专业冷静" |
| system_prompt | string | 是 | 系统提示词 |
| response_style | string | 否 | 响应风格描述 |

### 1.5 Memory (共享记忆)

聊天室中所有 Agent 共享的对话历史。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| messages | list[Message] | 是 | 消息列表 |
| max_tokens | int | 否 | 最大 token 数，默认 100000 |
| created_at | timestamp | 是 | 创建时间 |

### 1.6 Message (消息)

对话中的单条消息。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 唯一标识 |
| role | string | 是 | 角色：user/agent |
| agent_id | string | 否 | Agent ID（agent 角色时） |
| content | string | 是 | 消息内容 |
| timestamp | timestamp | 是 | 时间戳 |

---

## 2. 关系图

```
┌─────────────┐       ┌─────────────┐
│  Chatroom  │──────▶│    Agent    │
│             │ 1  *  │             │
└─────────────┘       └─────────────┘
      │                      │
      │                      ▼
      │               ┌─────────────┐
      │               │  Personality │
      │               └─────────────┘
      │
      ▼
┌─────────────┐       ┌─────────────┐
│   Memory    │──────▶│   Message   │
│             │ 1  *  │             │
└─────────────┘       └─────────────┘
```

---

## 3. 验证规则

| 实体 | 规则 |
|------|------|
| Chatroom.name | 长度 1-100 字符 |
| Chatroom.max_members | 1-100 之间 |
| Agent.name | 长度 1-50 字符，不能重复 |
| Agent.model_provider | 必须是有效的 ModelProvider |
| Agent.api_url | 如果 model_provider 是 custom，则必填 |
| Personality.system_prompt | 长度 1-2000 字符 |
| Memory.max_tokens | 正整数，默认 100000 |
