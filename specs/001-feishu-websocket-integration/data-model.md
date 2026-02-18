# 数据模型：飞书 Skill 集成

**功能**: 001-feishu-websocket-integration
**日期**: 2026-02-18

## 实体

### LongConnectionPlatform (抽象基类)

所有长连接平台实现的通用接口。

| 方法 | 返回类型 | 描述 |
|------|----------|------|
| connect() | Awaitable[None] | 建立长连接 |
| disconnect() | Awaitable[None] | 断开连接 |
| on_message(callback) | None | 注册消息回调 |
| on_error(callback) | None | 注册错误回调 |
| is_connected() | bool | 检查连接状态 |

### LongConnectionRegistry (单例)

长连接平台注册中心。

| 方法 | 返回类型 | 描述 |
|------|----------|------|
| register(platform) | None | 注册平台实现 |
| unregister(platform_id) | None | 注销平台 |
| get(platform_id) | LongConnectionPlatform | 获取平台实例 |
| get_all() | List[LongConnectionPlatform] | 获取所有已注册平台 |
| clear() | None | 清除所有注册 |

### FeishuConfig

飞书集成的配置，从 config.yaml 加载。

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| enabled | bool | 是 | 飞书 Skill 的主开关 |
| app_id | str | 是 | 飞书应用 ID |
| app_secret | str | 是 | 飞书应用密钥 |
| encrypt_key | str | 否 | 消息加密密钥（可选） |
| max_sessions | int | 否 | 最大并发会话数（默认：100） |
| session_timeout | int | 否 | 会话超时秒数（默认：3600） |
| reconnect_initial_delay | float | 否 | 初始重连延迟（默认：1.0） |
| reconnect_max_delay | float | 否 | 最大重连延迟（默认：30.0） |
| reconnect_max_retries | int | 否 | 最大连续重试次数（默认：10） |

**验证规则**:
- enabled 存在时，app_id 必须以 "cli_" 开头
- enabled 存在时，app_secret 必须非空
- max_sessions 必须为正数
- session_timeout 必须 >= 60

### FeishuSession

表示活跃的用户对话会话。

| 字段 | 类型 | 描述 |
|------|------|------|
| open_id | str | 飞书用户标识符（主键） |
| agent | Agent | 此用户的 Agent 实例 |
| created_at | datetime | 会话创建时间戳 |
| last_activity | datetime | 最后消息时间戳 |
| message_count | int | 此会话中的消息总数 |

**状态转换**:
```
[新建] --(首条消息)--> [活跃]
[活跃] --(新消息)--> [活跃] (更新 last_activity)
[活跃] --(超时)--> [过期] --> [移除]
[活跃] --(清理)--> [移除]
```

### FeishuEvent

从飞书 WebSocket 解析的传入事件。

| 字段 | 类型 | 描述 |
|------|------|------|
| event_id | str | 唯一事件标识符 |
| event_type | str | 事件类型（如："im.message.receive_v1"） |
| open_id | str | 发送者的飞书用户 ID |
| message_id | str | 消息标识符 |
| content | str | 消息文本内容 |
| timestamp | datetime | 事件时间戳 |

### FeishuSkill

飞书平台的 LongConnectionPlatform 实现。

| 字段 | 类型 | 描述 |
|------|------|------|
| config | FeishuConfig | 飞书配置 |
| ws_client | FeishuWSClient | WebSocket 客户端 |
| session_manager | SessionManager | 会话管理器 |
| message_sender | FeishuMessageSender | 消息发送器 |
| _message_callback | Callable | 消息回调函数 |
| _error_callback | Callable | 错误回调函数 |

## 关系

```
┌─────────────────────────────────────┐
│     LongConnectionRegistry          │
│           (单例)                     │
└──────────────┬──────────────────────┘
               │ 注册
               ▼
┌─────────────────────────────────────┐
│   LongConnectionPlatform            │
│        (抽象基类)                    │
└──────────────┬──────────────────────┘
               │ 实现
               ▼
┌─────────────────────────────────────┐
│        FeishuSkill                  │
│  (实现 LongConnectionPlatform)       │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌─────────────┐   ┌─────────────┐
│ ws_client   │   │ SessionMgr  │
└─────────────┘   └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │FeishuSession│
                  │ (每用户)    │
                  └─────────────┘
```

## 集成流程

```python
# Agent 启动时 (cli.py)
from mini_agent.long_connection import LongConnectionRegistry
from mini_agent.skills.feishu_skill import FeishuSkill

# 根据配置决定是否加载
if config.feishu.enabled:
    feishu_skill = FeishuSkill(config)
    LongConnectionRegistry.register(feishu_skill)
    # Skill 会自动 connect() 并开始监听
```

## 不变式

- LongConnectionRegistry 是单例，整个应用生命周期内只有一个实例
- 每个平台 ID 在注册中心中最多存在一个实例
- FeishuSkill.get_or_create(open_id) 为每个用户维护独立会话
- 禁用 Skill（enabled: false）时，不创建任何实例
