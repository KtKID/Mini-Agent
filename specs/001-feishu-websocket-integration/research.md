# 研究：飞书 Skill 集成

**功能**: 001-feishu-websocket-integration
**日期**: 2026-02-18

## 技术决策

### 1. 长连接框架架构

**决策**: 事件驱动回调模式，而非轮询

**理由**:
- Agent 已有事件循环机制
- 回调模式更符合现有架构
- 避免在 while true 中添加逻辑
- 资源效率更高（无忙等待）

**备选方案**:
| 备选方案 | 拒绝原因 |
|---------|----------|
| Agent 主循环中轮询 | 破坏现有架构，复杂度高 |
| 独立进程 | 重复资源，不是真正的 Skill 集成 |

### 2. Skill 注册机制

**决策**: 基于现有 Skill 系统扩展，使用 LongConnectionRegistry

**理由**:
- 利用现有 Skill 基础设施
- 标准化接口，便于扩展
- 与现有 Skill 加载器兼容

### 3. Feishu SDK 选择

**决策**: 使用官方 `lark-oapi` Python SDK

**理由**:
- 由飞书/Lark 团队维护的官方 SDK
- 原生支持 WebSocket 长连接模式
- 处理认证、令牌刷新和事件解析

**备选方案**:
| 备选方案 | 拒绝原因 |
|---------|----------|
| 手动实现 WebSocket | 复杂度更高，需要处理所有协议细节 |
| 第三方 SDK | 可靠性较低，可能不跟随最新 API 变化 |

### 4. 会话存储策略

**决策**: 内存字典配合 TTL 清理

**理由**:
- MVP 范围：50 个并发会话轻松放入内存
- 规格中无持久化要求
- 简单实现，无需外部依赖
- 以后可升级到 Redis

**备选方案**:
| 备选方案 | 拒绝原因 |
|---------|----------|
| Redis | MVP 过度设计，增加部署复杂度 |
| SQLite | 文件 I/O 开销，不必要用于临时会话 |

### 5. 并发模型

**决策**: asyncio 配合每用户消息队列

**理由**:
- 与现有 Agent 异步设计一致
- 自然适合 WebSocket I/O
- 每用户队列防止快速发送消息的竞态条件
- 非阻塞允许并发多用户处理

### 6. 重连策略

**决策**: 指数退避配合最大重试次数

**理由**:
- 行业标准的弹性连接方式
- 防止服务恢复时的惊群效应
- 每次尝试都记录以便调试
- 参数：初始 1 秒延迟，最大 30 秒延迟，最大 10 次重试

## 集成模式

### 事件流程

```
Agent 启动:
1. 加载配置中的 feishu.enabled
2. FeishuSkill.__init__() 被调用
3. FeishuSkill.connect() 建立 WebSocket 连接
4. 进入事件监听循环

飞书事件到达:
1. WebSocket 接收事件
2. FeishuEventHandler.parse() 提取 open_id、消息内容
3. SessionManager.get_or_create(open_id) 获取会话
4. 调用 Agent.add_user_message() 添加消息
5. Agent 处理并返回响应
6. FeishuMessageSender.send_text() 发送回复
```

### 可插拔机制

```python
# config.yaml
feishu:
  enabled: true  # 设为 false 即禁用

# cli.py 伪代码
if config.feishu.enabled:
    from mini_agent.skills.feishu_skill import FeishuSkill
    skill = FeishuSkill(config)
    LongConnectionRegistry.register(skill)
```

### 错误处理层级

| 层级 | 错误类型 | 处理方式 |
|------|----------|----------|
| WebSocket | 连接丢失 | 自动退避重连 |
| 事件解析 | 格式无效 | 记录并跳过，继续监听 |
| Agent | 处理错误 | 返回错误消息给用户 |
| API | 发送失败 | 退避重试，记录如果耗尽 |

## 配置架构

```yaml
feishu:
  enabled: true                    # 开关，禁用后不加载
  app_id: "cli_xxxxxxxxxx"
  app_secret: "xxxxxxxxxx"
  encrypt_key: ""                  # 可选，用于消息加密

  session:
    max_sessions: 100              # 最大并发会话数
    timeout: 3600                  # 会话超时秒数 (1小时)

  reconnect:
    initial_delay: 1               # 初始重连延迟 (秒)
    max_delay: 30                 # 最大重连延迟 (秒)
    max_retries: 10                # 最大连续重试次数
```

## 参考资料

- [飞书开放平台 - 事件订阅](https://open.feishu.cn/document/server-docs/event-subscription-guide/overview)
- [飞书 Python SDK 文档](https://open.feishu.cn/document/server-docs/server-side-sdk/python-sdk)
- [lark-oapi PyPI](https://pypi.org/project/lark-oapi/)
- 现有项目: `docs/FEISHU_INTEGRATION_DESIGN.md`
