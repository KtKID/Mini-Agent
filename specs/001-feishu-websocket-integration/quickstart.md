# 快速开始：飞书 Skill 集成

**功能**: 001-feishu-websocket-integration
**日期**: 2026-02-18

## 概述

飞书 Skill 是 Mini Agent 的可插拔组件，通过 WebSocket 长连接接收飞书用户消息，并将响应发送回飞书。

### 架构特点

- **可插拔**: 通过配置启用/禁用，不影响 Agent 原有功能
- **事件驱动**: 使用回调机制，非轮询
- **通用框架**: 基于 LongConnectionPlatform 接口，便于扩展其他平台

## 前置条件

1. **飞书开发者账号**
   - 在[飞书开放平台](https://open.feishu.cn)注册
   - 创建企业自建应用
   - 获取 App ID 和 App Secret

2. **Mini Agent 配置**
   - Mini Agent 已安装并配置
   - LLM API 凭证已在 `config.yaml` 中配置

## 步骤 1：配置飞书应用

### 1.1 启用事件订阅

1. 在飞书开放平台进入你的应用
2. 进入 **事件与回调** → **事件配置**
3. 订阅方式选择 **使用长连接接收事件**
4. 添加事件：`im.message.receive_v1`（接收消息）

### 1.2 配置权限

在 **权限管理** 中添加以下权限：

| 权限 | 名称 | 用途 |
|------|------|------|
| `im:message` | 获取与发送单聊、群组消息 | 发送/接收消息 |
| `im:message:send_as_bot` | 以应用身份发消息 | Bot 身份 |

### 1.3 发布应用

1. 进入 **版本管理与发布**
2. 创建版本并提交审批
3. 审批通过后，为你的组织启用应用

### 1.4 添加 Bot 为联系人

用户必须在消息交互前将 bot 添加为联系人。

## 步骤 2：配置 Mini Agent

### 2.1 更新 config.yaml

在 `config.yaml` 中添加飞书配置：

```yaml
# 现有 Mini Agent 配置
api_key: "your-llm-api-key"
api_base: "https://api.minimax.io"
model: "MiniMax-M2.5"

# 添加飞书 Skill 配置
feishu:
  enabled: true                    # 设为 false 即可禁用
  app_id: "cli_xxxxxxxxxx"        # 你的飞书 App ID
  app_secret: "xxxxxxxxxx"         # 你的飞书 App Secret

  session:
    max_sessions: 100              # 最大并发用户数
    timeout: 3600                  # 会话超时（秒）
```

### 2.2 安装飞书 SDK

```bash
uv pip install lark-oapi
```

## 步骤 3：运行 Agent

### 3.1 启动 Agent

```bash
# 正常启动，Feishu Skill 会被自动加载
uv run python -m mini_agent.cli
```

### 3.2 禁用飞书 Skill

如需禁用飞书功能，只需修改配置：

```yaml
feishu:
  enabled: false  # 禁用飞书 Skill
```

重启 Agent 后，飞书连接不会被建立，但 Agent 的原有 CLI 功能完全正常。

### 3.3 验证连接

查看以下日志信息：

```
[INFO] Agent: Initializing FeishuSkill...
[INFO] FeishuSkill: Connecting to Feishu WebSocket...
[INFO] FeishuSkill: WebSocket connection established
[INFO] FeishuSkill: Listening for events...
```

## 步骤 4：测试集成

### 4.1 发送测试消息

1. 打开飞书应用
2. 在联系人中找到你的 bot
3. 发送消息："你好"

### 4.2 预期响应

Bot 应在 30 秒内回复相关响应。

## 禁用/移除 Skill

### 方式一：禁用（推荐）

修改配置即可：

```yaml
feishu:
  enabled: false
```

### 方式二：完全移除

删除 `mini_agent/skills/feishu_skill/` 目录即可。Agent 会正常启动，无任何错误。

## 故障排查

### 连接问题

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| "Connection failed" | app_id/secret 无效 | 在飞书控制台验证凭证 |
| "WebSocket 断开" | 网络问题 | 检查防火墙是否允许 wss:// |
| 未收到事件 | 事件未订阅 | 在控制台添加 `im.message.receive_v1` |

### Skill 未加载

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 无飞书日志 | enabled: false | 检查配置 |
| 导入错误 | 缺少 lark-oapi | uv pip install lark-oapi |

## 配置参考

### 完整配置示例

```yaml
feishu:
  enabled: true                    # 开关，禁用后不加载
  app_id: "cli_xxxxxxxxxx"
  app_secret: "xxxxxxxxxx"
  encrypt_key: ""                  # 可选，用于加密事件

  session:
    max_sessions: 100              # 最大并发用户会话数
    timeout: 3600                  # 会话超时秒数

  reconnect:
    initial_delay: 1.0             # 初始重连延迟（秒）
    max_delay: 30.0                # 最大重连延迟（秒）
    max_retries: 10                # 最大连续重试次数
```

## 下一步

- **多用户测试**: 让多位同事同时向 bot 发送消息
- **长对话测试**: 测试跨多条消息的上下文保留
- **监控日志**: 观察重连事件和错误模式
- **扩展其他平台**: 实现 LongConnectionPlatform 接口添加新平台
