# Feishu Skill

飞书消息平台集成插件，提供与飞书消息服务的 WebSocket 长连接支持。

## 1. 简介

Feishu Skill 是 Mini-Agent 的一个可选插件，实现与飞书（Feishu/Lark）消息平台的长连接集成。

### 功能特性

- **WebSocket 长连接**：使用飞书 SDK 保持稳定的 WebSocket 连接
- **多用户会话隔离**：支持多用户并发会话管理
- **自动重连**：连接断开时自动重连
- **消息收发**：接收和发送文本消息
- **消息操作**：回复、读取、删除消息
- **表情反应**：对消息添加表情回应（送心、点赞等）
- **独立日志**：专门的日志文件 `logs/feishu.log`

## 2. 前置要求

### 2.1 飞书开放平台账号

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 注册并登录企业账号
3. 创建企业自建应用

### 2.2 创建企业自建应用

1. 进入「应用创建页面」
2. 选择「企业自建应用」
3. 填写应用名称和描述
4. 创建应用后，在「应用凭证」页面获取：
   - App ID
   - App Secret

### 2.3 开通权限

在「权限管理」页面开通以下权限：

| 权限名称 | 权限说明 |
|---------|---------|
| im:message:send_as_bot | 以应用身份发送消息 |
| im:message:send_as_bot_allow_api | 接收消息 |
| im:message:reply | 回复消息 |
| im:message:get | 获取消息内容 |
| im:message.delete | 删除消息 |
| im:messageReaction:create | 添加消息反应 |

### 2.4 事件订阅配置

1. 在「事件订阅」页面添加事件：
   - `im.message.receive_v1` - 接收消息事件
2. 配置订阅请求 URL（需要可公网访问的地址）
3. 获取并填写：
   - Verification Token（校验令牌）
   - （可选）Encrypt Key（加密密钥）用于消息加密

## 3. 安装配置

### 3.1 安装依赖

项目已包含 `lark-oapi` 依赖，无需单独安装：

```bash
uv sync
```

### 3.2 环境变量配置

可以通过环境变量配置飞书凭证：

```bash
export FEISHU_APP_ID="cli_xxxxx"
export FEISHU_APP_SECRET="xxxxx"
export FEISHU_TEST_OPEN_ID="ou_xxxxx"  # 可选，用于测试
```

### 3.3 config.yaml 配置

在 `mini_agent/config/config.yaml` 中配置：

```yaml
feishu:
  enabled: true                    # 是否启用
  app_id: "cli_xxxxx"              # 应用 App ID
  app_secret: "xxxxx"              # 应用 App Secret
  # encrypt_key: ""                 # 加密密钥（可选）
  session_timeout: 300              # 会话超时时间（秒），默认 300
  max_sessions: 10                 # 最大并发会话数，默认 10
```

### 配置项说明

| 配置项 | 必填 | 说明 |
|--------|------|------|
| enabled | 是 | 是否启用飞书 Skill |
| app_id | 是 | 飞书应用 ID，以 `cli_` 开头 |
| app_secret | 是 | 飞书应用密钥 |
| encrypt_key | 否 | 消息加密密钥（可选） |
| session_timeout | 否 | 用户会话超时时间（秒），默认 300 |
| max_sessions | 否 | 最大并发会话数，默认 10 |

> 注意：飞书 SDK 会自动处理 verification token，用户无需配置。

## 4. 功能列表

| 功能 | 说明 |
|------|------|
| WebSocket 长连接 | 通过飞书 SDK 维护持久的 WebSocket 连接 |
| 消息接收 | 接收用户发送给应用的消息 |
| 消息发送 | 向用户发送文本消息 |
| 消息回复 | 回复指定消息 |
| 消息读取 | 获取消息详细内容 |
| 消息删除 | 删除指定消息 |
| 表情反应 | 对消息添加表情（送心、点赞等） |
| 会话管理 | 自动管理用户会话，支持超时清理 |

## 5. 使用方法

### 5.1 启用/禁用

在 `config.yaml` 中设置：

```yaml
feishu:
  enabled: true   # 设为 false 即可禁用
```

### 5.2 Agent 回调设置

FeishuSkill 支持设置 Agent 回调函数来处理接收到的消息：

```python
from mini_agent.skills.feishu_skill import FeishuSkill
from mini_agent.skills.feishu_skill.config import FeishuConfig

# 创建配置（SDK 自动处理 verification token）
config = FeishuConfig(
    enabled=True,
    app_id="cli_xxxxx",
    app_secret="xxxxx"
)

# 创建 Skill 实例
skill = FeishuSkill(config)

# 设置 Agent 回调函数
async def handle_message(user_id: str, message: str) -> str:
    # 这里可以调用 AI Agent 处理消息
    return f"收到消息: {message}"

skill.set_agent_callback(handle_message)

# 连接飞书（SDK 自动处理 verification token）
await skill.connect()
```

### 5.3 不使用 Agent 回调

如果不设置 Agent 回调，Skill 只会接收消息并自动回复"送心"表情，不会进行智能回复：

```python
skill = FeishuSkill(config)
await skill.connect()
# 收到消息时会自动回复 ❤️ 表情
```

## 6. API 参考

### 6.1 send_text()

向用户发送文本消息。

```python
async def send_text(receive_id: str, text: str) -> str:
    """
    Args:
        receive_id: 用户 open_id
        text: 消息内容
    Returns:
        消息 ID
    """
```

### 6.2 reply_message()

回复指定消息。

```python
async def reply_message(message_id: str, text: str) -> str:
    """
    Args:
        message_id: 被回复的消息 ID
        text: 回复内容
    Returns:
        新消息 ID
    """
```

### 6.3 get_message()

获取消息内容。

```python
async def get_message(message_id: str) -> dict:
    """
    Args:
        message_id: 消息 ID
    Returns:
        消息数据字典，包含 message_id, content, msg_type
    """
```

### 6.4 delete_message()

删除指定消息。

```python
async def delete_message(message_id: str) -> bool:
    """
    Args:
        message_id: 消息 ID
    Returns:
        是否删除成功
    """
```

### 6.5 create_reaction()

对消息添加表情反应。

```python
async def create_reaction(message_id: str, emoji_id: str = "SMILE") -> bool:
    """
    Args:
        message_id: 消息 ID
        emoji_id: 表情 ID
    Returns:
        是否添加成功
    """
```

**可用表情 ID：**

| 表情 ID | 说明 |
|---------|------|
| SMILE | 笑脸 |
| LAUGH | 大笑 |
| CRY | 哭 |
| HEART | 心 |
| LOVE | 送心 |
| CLAP | 鼓掌 |
| WAVE | 挥手 |
| OK | 点赞 |

## 7. 日志说明

### 7.1 日志文件位置

日志文件位于项目根目录：`logs/feishu.log`

### 7.2 日志级别

默认日志级别为 INFO，可在代码中调整。

### 7.3 日志格式

```
2026-02-18 11:38:20 [INFO] mini_agent.feishu: FeishuSkill: [CONNECT_START] app_id=cli_a91e23...
2026-02-18 11:45:08 [INFO] mini_agent.feishu: FeishuSkill: [RECV] from=ou_xxx msg_id=om_xxx content='你好'
2026-02-18 11:45:08 [INFO] mini_agent.feishu: FeishuSkill: [PROCESS] from=ou_xxx msg_id=om_xxx
```

### 7.4 日志标签含义

| 标签 | 说明 |
|------|------|
| CONNECT_START | 开始连接 |
| CONNECTED | 连接成功 |
| RECV | 收到消息 |
| PROCESS | 处理消息 |
| SEND_TEXT | 发送消息 |
| REPLY | 回复消息 |
| REACTION_ADD | 添加反应 |
| DISCONNECT | 断开连接 |
| ERROR | 错误 |

## 8. 自动化测试

### 8.1 测试内容

自动化测试覆盖以下功能：

| 测试组 | 测试项 |
|--------|--------|
| 配置验证 | 禁用配置、app_id 格式验证 |
| SDK 导入 | SDK 模块导入、消息 API 可用性 |
| 消息构建 | 发送、回复、读取、删除消息请求构建 |
| Skill 初始化 | 启用状态、平台 ID |
| 真实 API | 发送消息、回复消息、读取消息、添加反应 |

### 8.2 环境变量配置

运行测试前需要配置以下环境变量：

```bash
# 必需
export FEISHU_APP_ID="cli_xxxxx"
export FEISHU_APP_SECRET="xxxxx"

# 可选 - 用于真实 API 测试
export FEISHU_TEST_OPEN_ID="ou_xxxxx"
```

或者在运行时指定：

```bash
FEISHU_APP_ID=cli_xxx FEISHU_APP_SECRET=xxx FEISHU_TEST_OPEN_ID=ou_xxx uv run python -m tests.feishu.test_feishu_skill
```

### 8.3 运行命令

```bash
# 完整测试（需要配置环境变量）
uv run python -m tests.feishu.test_feishu_skill
```

### 8.4 测试结果解读

测试输出示例：

```
==================================================
Feishu Skill 自动化测试
==================================================

环境配置:
  FEISHU_APP_ID: 已设置
  FEISHU_APP_SECRET: 已设置
  FEISHU_TEST_OPEN_ID: 已设置

[测试 1] 配置验证
  ✅ 禁用配置验证
  ✅ 有效配置验证
  ✅ app_id格式验证

[测试 2] SDK 导入
  ✅ SDK 导入
  ✅ 消息 API 可用

[测试 3] 消息构建
  ✅ 发送消息请求构建
  ✅ 回复消息请求构建
  ✅ 读取消息请求构建
  ✅ 删除消息请求构建

[测试 4] FeishuSkill 初始化
  ✅ Skill 启用状态
  ✅ 平台 ID

[测试 5] 真实 API 消息操作
  ✅ 发送消息成功: om_xxx
  ✅ 回复消息成功
  ✅ 读取消息成功
  ✅ 添加反应成功

==================================================
测试结果: 15 通过, 0 失败
==================================================
```

**结果说明：**
- 全部通过：所有功能正常工作
- 有失败：查看失败详情中的错误信息进行排查

### 8.5 注意事项

1. 真实 API 测试会向配置的测试用户发送消息
2. 确保 `FEISHU_TEST_OPEN_ID` 对应的用户是应用的可信用户
3. 测试消息会真实发送到飞书

## 9. 常见问题

### Q1: 连接失败，提示"配置无效"

检查 `config.yaml` 中的配置：
- `app_id` 是否以 `cli_` 开头
- `app_secret` 是否正确

> 注意：飞书 SDK 会自动处理 verification token，无需用户配置。

### Q2: 收不到消息

1. 确认应用已在飞书开放平台开通 `im:message:send_as_bot_allow_api` 权限
2. 确认已在事件订阅中添加 `im.message.receive_v1` 事件
3. 检查 `logs/feishu.log` 日志中的错误信息

### Q3: 发送消息失败

1. 确认应用已开通 `im:message:send_as_bot` 权限
2. 检查日志中的具体错误信息

### Q4: 添加反应失败

确认应用已开通 `im:messageReaction:create` 权限。

### Q5: 如何查看日志

```bash
# 实时查看日志
tail -f logs/feishu.log

# 查看最近 100 行
tail -n 100 logs/feishu.log
```

## 10. 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                    Mini-Agent                           │
├─────────────────────────────────────────────────────────┤
│                   FeishuSkill                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  WebSocket  │  │   IM API    │  │   Session   │   │
│  │   Client    │  │   Service   │  │   Manager   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
├─────────────────────────────────────────────────────────┤
│                   飞书开放平台                          │
│  ┌─────────────┐  ┌─────────────┐                     │
│  │   WebSocket │  │   REST API  │                     │
│  │   长连接    │  │   接口      │                     │
│  └─────────────┘  └─────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

- **WebSocket Client**：使用飞书 SDK 维护长连接，接收用户消息
- **IM Service**：调用飞书 REST API 发送消息、回复、添加反应等
- **Session Manager**：管理用户会话，跟踪会话活跃状态

## 11. 卸载/禁用

如需禁用飞书 Skill：

1. 在 `config.yaml` 中设置：
   ```yaml
   feishu:
     enabled: false
   ```

2. 或删除相关配置整个块

## 12. 更新日志

### v1.0.0
- 初始版本
- 支持消息收发、回复、读取、删除
- 支持表情反应
- 支持会话管理
