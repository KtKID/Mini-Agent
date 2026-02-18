# 飞书事件合约

**功能**: 001-feishu-websocket-integration
**日期**: 2026-02-18

本文档定义 Mini Agent 与飞书开放平台之间的合约，以及与 Agent 的集成接口。

## LongConnectionPlatform 接口

所有长连接平台实现的通用接口。

```python
from abc import ABC, abstractmethod
from typing import Callable, Awaitable

class LongConnectionPlatform(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """建立长连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def on_message(self, callback: Callable[[str, str], Awaitable[None]]) -> None:
        """
        注册消息回调

        Args:
            callback: 回调函数，参数为 (user_id: str, message: str)
        """
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[Exception], Awaitable[None]]) -> None:
        """
        注册错误回调

        Args:
            callback: 回调函数，参数为 (error: Exception)
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass
```

## LongConnectionRegistry 接口

```python
class LongConnectionRegistry:
    def register(self, platform: LongConnectionPlatform) -> None:
        """注册平台实现"""
        pass

    def unregister(self, platform_id: str) -> None:
        """注销平台"""
        pass

    def get(self, platform_id: str) -> LongConnectionPlatform:
        """获取平台实例"""
        pass

    def get_all(self) -> list[LongConnectionPlatform]:
        """获取所有已注册平台"""
        pass

    def clear(self) -> None:
        """清除所有注册"""
        pass
```

---

## 传入事件（飞书 → Mini Agent）

### im.message.receive_v1

当用户向 bot 发送消息时接收。

**触发**: 用户在飞书中向 bot 发送文本消息

**事件架构**:
```json
{
  "id": "string (唯一事件 ID)",
  "type": "event_callback",
  "header": {
    "event_id": "string",
    "event_type": "im.message.receive_v1",
    "create_time": "string (ISO 8601 时间戳)",
    "token": "string (验证令牌)",
    "app_id": "string",
    "tenant_key": "string"
  },
  "event": {
    "sender": {
      "sender_id": {
        "open_id": "string (用户的 open_id，如 'ou_xxx')",
        "user_id": "string (内部用户 ID)",
        "union_id": "string"
      },
      "sender_type": "app",
      "tenant_key": "string"
    },
    "message": {
      "message_id": "string",
      "root_id": "string (父消息 ID，如果是回复)",
      "parent_id": "string",
      "create_time": "string (ISO 8601)",
      "chat_id": "string",
      "chat_type": "p2p",
      "message_type": "text",
      "content": "string (JSON 编码的内容)",
      "mentions": []
    }
  }
}
```

**内容架构（文本消息）**:
```json
{
  "text": "用户的消息文本"
}
```

**Mini Agent 处理**:
1. 从 `event.sender.sender_id.open_id` 提取 `open_id`
2. 解析 `content` JSON 提取 `text`
3. 通过回调将 (open_id, text) 传递给 Agent
4. Agent 处理并返回响应

---

## 传出 API 调用（Mini Agent → 飞书）

### POST /im/v1/messages

向飞书用户发送消息。

**端点**: `https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id`

**认证**: Bearer 令牌 (tenant_access_token)

**请求头**:
```
Authorization: Bearer <tenant_access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "receive_id": "ou_xxx",
  "msg_type": "text",
  "content": "{\"text\":\"回复消息\"}"
}
```

**成功响应 (200)**:
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "message_id": "om_xxx"
  }
}
```

**错误响应**:

| 代码 | 描述 | 处理方式 |
|------|------|----------|
| 99991663 | 无效的 receive_id | 记录错误，跳过消息 |
| 99991661 | 令牌过期 | 刷新令牌，重试一次 |
| 99991400 | 速率限制 | 退避 60 秒，重试 |

---

### POST /auth/v3/tenant_access_token/internal

获取用于 API 调用的租户访问令牌。

**端点**: `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`

**请求体**:
```json
{
  "app_id": "cli_xxx",
  "app_secret": "xxx"
}
```

**成功响应 (200)**:
```json
{
  "code": 0,
  "msg": "ok",
  "tenant_access_token": "t-xxx",
  "expire": 7200
}
```

**令牌缓存**:
- 缓存令牌直到 `expire - 60` 秒
- 过期前主动刷新
- 处理 401 响应：刷新并重试

---

## WebSocket 连接

### 连接建立

**端点**: `wss://ws.feishu.cn/sky/...` (通过 SDK 获取)

**协议**: TLS 上的 WebSocket

**心跳**: 每 30 秒发送 ping，期望在 10 秒内收到 pong

**重连**:
- 断开时，等待指数退避时间
- 初始延迟：1 秒
- 最大延迟：30 秒
- 放弃前最大重试次数：10

---

## 错误处理合约

| 错误来源 | 错误类型 | 恢复操作 |
|----------|----------|----------|
| WebSocket | 连接丢失 | 退避重连 |
| WebSocket | 心跳超时 | 重连 |
| 事件解析 | 无效 JSON | 记录，跳过事件 |
| 事件解析 | 缺少字段 | 记录，跳过事件 |
| API 调用 | 401 未授权 | 刷新令牌，重试一次 |
| API 调用 | 429 速率限制 | 退避 60 秒，重试 |
| API 调用 | 5xx 服务器错误 | 退避 5 秒，重试最多 3 次 |
| Agent | 处理超时 | 返回错误消息给用户 |
| Agent | 异常 | 返回通用错误，记录详细信息 |

---

## 消息流程时序

```
┌─────────┐     ┌─────────┐     ┌────────────┐     ┌──────────────┐
│  用户   │     │  飞书   │     │ FeishuSkill │     │    LLM API   │
└────┬────┘     └────┬────┘     └─────┬──────┘     └──────┬───────┘
     │               │                │                   │
     │ 发送消息      │                │                   │
     │──────────────▶│                │                   │
     │               │                │                   │
     │               │ WebSocket 事件│                   │
     │               │───────────────▶│                   │
     │               │                │                   │
     │               │                │ 回调 (open_id, text) │
     │               │                │─────────────────▶│
     │               │                │                   │
     │               │                │ LLM 请求          │
     │               │                │──────────────────▶│
     │               │                │                   │
     │               │                │ LLM 响应          │
     │               │                │◀──────────────────│
     │               │                │                   │
     │               │                │ POST /messages    │
     │               │                │─────────────────▶│
     │               │                │                   │
     │ 收到回复      │                │                   │
     │◀─────────────│                │                   │
     │               │                │                   │
```
