# 飞书集成设计方案

## 概述

本文档描述如何将 Mini Agent 与飞书 Bot 集成，实现用户在飞书中与 Agent 对话的功能。

## 飞书支持的两种事件接收方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| **Webhook 回调** | 需要公网 IP/域名，飞书主动推送 | 生产环境、有服务器 |
| **WebSocket 长连接** | 无需公网 IP，SDK 主动建立连接 | 开发测试、无公网服务器 |

**推荐方案**：WebSocket 长连接（无需公网 IP，本地即可调试）

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Mini Agent + Feishu 集成架构                          │
└─────────────────────────────────────────────────────────────────────────────┘

                              飞书云端
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐   │
│  │  飞书用户   │────▶│  飞书 Bot   │────▶│  飞书开放平台事件服务       │   │
│  │  (对话)     │     │  (消息入口) │     │  im.message.receive_v1     │   │
│  └─────────────┘     └─────────────┘     └──────────────┬──────────────┘   │
└─────────────────────────────────────────────────────────┼───────────────────┘
                                                          │
                                                   WebSocket 长连接
                                                          │
┌─────────────────────────────────────────────────────────┼───────────────────┐
│                          本地服务                         │                   │
│  ┌──────────────────────────────────────────────────────┴───────────────┐   │
│  │                      Feishu Adapter (新增)                            │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │   │
│  │  │ WebSocket Client│  │  Event Handler  │  │  Message Sender     │   │   │
│  │  │ (飞书SDK)        │  │  (事件处理)     │  │  (飞书API回复)      │   │   │
│  │  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘   │   │
│  │           │                    │                      │              │   │
│  │           └────────────────────┼──────────────────────┘              │   │
│  └────────────────────────────────┼─────────────────────────────────────┘   │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Session Manager (新增)                            │   │
│  │  • 会话 ID 映射 (飞书 open_id -> Agent session)                      │   │
│  │  • 多用户隔离                                                        │   │
│  │  • 消息历史管理                                                      │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Agent (现有)                                   │   │
│  │  • LLMClient                                                        │   │
│  │  • Tools (File, Bash, MCP, Skills)                                  │   │
│  │  • 执行循环                                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │   飞书 API      │
                          │  (发送回复消息)  │
                          └─────────────────┘
```

## 当前 Agent 设计分析

### 现有架构：请求-响应模式

当前 Agent 不具备循环监听 WebSocket 的能力，采用单次执行模式：

```
┌─────────────────┐
│   CLI (cli.py)  │
│  交互循环在这里  │
└────────┬────────┘
         │
         ▼
   ┌────────────┐
   │ agent.run()│  ← 单次执行，处理后返回
   └────────────┘
```

**特点**：
- `Agent.run()` 是单次执行，处理一条消息后返回
- 循环逻辑在 `cli.py` 的 `while True` 里，依赖用户手动输入
- 没有 WebSocket 服务器/客户端能力
- 没有事件监听机制

### 需要新增的架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     新架构：事件驱动 + 会话管理                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         Event Loop (新增)                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     FeishuService (新增)                             │   │
│  │                                                                      │   │
│  │   while True:  # 持续监听                                            │   │
│  │       event = await ws_client.receive()                             │   │
│  │       await self.handle_event(event)                                │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SessionManager (新增)                                    │
│                                                                              │
│   sessions = {                                                               │
│       "ou_xxx": Agent(session_1),    # 用户A的 Agent 实例                   │
│       "ou_yyy": Agent(session_2),    # 用户B的 Agent 实例                   │
│       "ou_zzz": Agent(session_3),    # 用户C的 Agent 实例                   │
│   }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Agent (现有，无需修改)                                   │
│                                                                              │
│   agent.add_user_message(msg)                                                │
│   await agent.run()  # 单次执行，处理后返回                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 关键区别

| 方面 | 当前 CLI 模式 | 飞书集成模式 |
|------|--------------|-------------|
| 事件来源 | 用户键盘输入 | WebSocket 消息 |
| 循环位置 | `cli.py` 的 `while True` | `FeishuService` 的事件循环 |
| 会话数 | 单会话（单用户） | 多会话（多用户隔离） |
| Agent 实例 | 全局唯一 | 每用户一个实例 |
| 响应方式 | 打印到终端 | 调用飞书 API |

## 数据流时序图

```
┌────────┐     ┌────────┐     ┌─────────────┐     ┌───────────────┐     ┌────────┐
│  用户  │     │飞书Bot │     │FeishuAdapter│     │SessionManager │     │ Agent  │
└───┬────┘     └───┬────┘     └──────┬──────┘     └───────┬───────┘     └───┬────┘
    │              │                 │                    │                 │
    │  发送消息    │                 │                    │                 │
    │─────────────▶│                 │                    │                 │
    │              │                 │                    │                 │
    │              │  触发事件       │                    │                 │
    │              │  im.message.    │                    │                 │
    │              │  receive_v1     │                    │                 │
    │              │────────────────▶│                    │                 │
    │              │                 │                    │                 │
    │              │                 │  解析事件          │                 │
    │              │                 │  (open_id, msg)    │                 │
    │              │                 │                    │                 │
    │              │                 │  获取/创建会话     │                 │
    │              │                 │───────────────────▶│                 │
    │              │                 │                    │                 │
    │              │                 │  返回 Agent 实例   │                 │
    │              │                 │◀───────────────────│                 │
    │              │                 │                    │                 │
    │              │                 │  调用 Agent.run()  │                 │
    │              │                 │────────────────────────────────────▶│
    │              │                 │                    │                 │
    │              │                 │                    │   LLM 调用     │
    │              │                 │                    │   工具执行     │
    │              │                 │                    │   ...          │
    │              │                 │                    │                 │
    │              │                 │  返回响应文本      │                 │
    │              │                 │◀────────────────────────────────────│
    │              │                 │                    │                 │
    │              │                 │  调用飞书API       │                 │
    │              │                 │  发送回复          │                 │
    │              │                 │────────────────────┼────────────────▶│
    │              │                 │                    │                 │
    │  收到回复    │                 │                    │                 │
    │◀─────────────│                 │                    │                 │
    │              │                 │                    │                 │
```

## 目录结构

```
mini_agent/
├── feishu/                      # 新增飞书集成模块
│   ├── __init__.py
│   ├── config.py                # 飞书配置 (App ID, Secret)
│   ├── ws_client.py             # WebSocket 长连接客户端
│   ├── event_handler.py         # 事件处理器
│   ├── message.py               # 消息发送/接收
│   ├── session_manager.py       # 会话管理器
│   └── service.py               # 飞书适配服务入口
├── agent.py                     # 现有，无需修改
└── cli.py                       # 现有，保持不变
```

## 核心模块设计

### 1. 飞书服务入口 (service.py)

```python
# mini_agent/feishu/service.py
class FeishuService:
    """飞书集成服务 - 持续监听 + 会话管理"""

    def __init__(self, config: FeishuConfig):
        self.ws_client = FeishuWSClient(config)
        self.session_manager = SessionManager(config)
        self.message_sender = FeishuMessageSender(config)

    async def start(self):
        """启动服务，建立长连接并持续监听"""
        # 1. 建立 WebSocket 长连接
        await self.ws_client.connect()

        # 2. 持续监听事件（这才是真正的循环）
        async for event in self.ws_client.listen():
            await self._handle_event(event)

    async def _handle_event(self, event: dict):
        """处理每个飞书事件"""
        # 解析事件
        open_id = event["event"]["sender"]["sender_id"]["open_id"]
        message = event["event"]["message"]["content"]

        # 获取该用户的 Agent 实例（每个用户独立）
        agent = self.session_manager.get_or_create(open_id)

        # 调用 Agent 处理（单次执行）
        agent.add_user_message(message)
        response = await agent.run()

        # 发送回复
        await self.message_sender.send_text(open_id, response)
```

### 2. 会话管理器 (session_manager.py)

```python
# mini_agent/feishu/session_manager.py
class SessionManager:
    """多用户会话管理"""

    def __init__(self, config):
        self.sessions: Dict[str, Agent] = {}  # open_id -> Agent
        self.config = config
        self._init_shared_resources()

    def _init_shared_resources(self):
        """初始化共享资源（LLM客户端、工具等）"""
        self.llm_client = LLMClient(...)
        self.tools = [...]
        self.system_prompt = "..."

    def get_or_create(self, open_id: str) -> Agent:
        """获取或创建用户的 Agent 实例"""
        if open_id not in self.sessions:
            # 为新用户创建独立的 Agent 实例
            self.sessions[open_id] = Agent(
                llm_client=self.llm_client,
                system_prompt=self.system_prompt,
                tools=self.tools,
                max_steps=self.config.max_steps,
            )
        return self.sessions[open_id]

    def remove(self, open_id: str):
        """移除用户会话"""
        if open_id in self.sessions:
            del self.sessions[open_id]

    def cleanup_expired(self, timeout: int = 3600):
        """清理过期会话"""
        # 实现会话超时清理逻辑
        pass
```

### 3. WebSocket 客户端 (ws_client.py)

```python
# mini_agent/feishu/ws_client.py
class FeishuWSClient:
    """飞书 WebSocket 长连接客户端"""

    def __init__(self, config: FeishuConfig):
        self.config = config
        self.ws = None

    async def connect(self):
        """建立 WebSocket 长连接"""
        # 使用飞书官方 SDK 或手动建立连接
        # 参考文档: https://open.feishu.cn/document/server-docs/event-subscription-guide/overview
        pass

    async def listen(self):
        """持续监听事件"""
        while True:
            event = await self._receive_event()
            if event:
                yield event

    async def _receive_event(self):
        """接收单个事件"""
        # 实现 WebSocket 消息接收逻辑
        pass

    async def close(self):
        """关闭连接"""
        if self.ws:
            await self.ws.close()
```

### 4. 消息发送 (message.py)

```python
# mini_agent/feishu/message.py
class FeishuMessageSender:
    """飞书消息发送器"""

    def __init__(self, config: FeishuConfig):
        self.config = config
        self.tenant_access_token = None

    async def _get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        # 调用飞书 API 获取 token
        pass

    async def send_text(self, open_id: str, text: str):
        """发送文本消息"""
        token = await self._get_tenant_access_token()
        # 调用飞书消息发送 API
        # POST /im/v1/messages?receive_id_type=open_id
        pass

    async def send_card(self, open_id: str, card: dict):
        """发送卡片消息"""
        pass
```

## 配置文件扩展

```yaml
# config.yaml 新增飞书配置
feishu:
  enabled: true
  app_id: "cli_xxxxxxxxxx"
  app_secret: "xxxxxxxxxx"
  encrypt_key: "xxxxxxxxxx"           # 可选，用于消息加密
  verification_token: "xxxxxxxxxx"    # 可选，用于事件验证

  # 会话配置
  session:
    max_sessions: 100                 # 最大并发会话数
    timeout: 3600                     # 会话超时时间（秒）
```

## 依赖安装

```bash
# 安装飞书官方 Python SDK
uv pip install lark-oapi
```

## 飞书开放平台配置

1. **创建应用**
   - 登录飞书开放平台：https://open.feishu.cn
   - 创建企业自建应用
   - 获取 App ID 和 App Secret

2. **配置事件订阅**
   - 进入「事件与回调」→「事件配置」
   - 订阅方式选择：「使用长连接接收事件」
   - 添加事件：`im.message.receive_v1`

3. **配置权限**
   - 添加「获取与发送单聊、群组消息」权限
   - 添加「读取用户信息」权限（可选）

4. **发布应用**
   - 配置完成后发布应用
   - 在飞书中添加 Bot 为联系人

## 运行命令

```bash
# 启动飞书集成服务
uv run mini-agent-feishu

# 或指定配置文件
uv run mini-agent-feishu --config /path/to/config.yaml
```

## pyproject.toml 扩展

```toml
[project.scripts]
mini-agent = "mini_agent.cli:main"
mini-agent-acp = "mini_agent.acp.server:main"
mini-agent-feishu = "mini_agent.feishu.service:main"  # 新增

[project.dependencies]
# ... 现有依赖
lark-oapi = ">=1.0.0"  # 新增飞书 SDK
```

## 注意事项

1. **会话隔离**：每个飞书用户需要独立的 Agent 实例，避免消息历史混淆

2. **并发处理**：多个用户同时发消息时，需要异步处理，避免阻塞

3. **错误处理**：WebSocket 断线重连、API 调用失败重试

4. **消息类型**：飞书支持文本、卡片、图片等多种消息类型，建议优先支持文本

5. **超时处理**：Agent 执行时间可能较长，考虑流式输出或分段回复

## 参考资料

- [飞书开放平台 - 事件订阅](https://open.feishu.cn/document/server-docs/event-subscription-guide/overview)
- [飞书开放平台 - 服务端 SDK](https://open.feishu.cn/document/server-docs/server-side-sdk)
- [飞书长连接：Python 开发者使用指南](https://www.zyfun.cn/338.html)
