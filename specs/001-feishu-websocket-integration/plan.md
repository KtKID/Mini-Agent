# 实现计划：飞书 Skill 集成

**分支**: `001-feishu-websocket-integration` | **日期**: 2026-02-18 | **规格**: [spec.md](./spec.md)
**输入**: 功能规格来自 `/specs/001-feishu-websocket-integration/spec.md`

## 概述

实现一个通用的长连接框架，使 Mini Agent 能够通过可插拔的 Skill 接收来自各种消息平台（如飞书）的消息。FeishuSkill 作为该框架的具体实现，通过 WebSocket 长连接接收飞书用户消息，通过回调机制传递给 Agent 处理。该设计确保 FeishuSkill 可以通过配置启用/禁用，删除后不影响 Agent 原有功能。

## 技术上下文

**语言/版本**: Python 3.11+
**主要依赖**: lark-oapi (飞书 SDK), pydantic (已有), asyncio (标准库)
**存储**: 内存会话存储 (MVP 无持久化)
**测试**: pytest 配合异步支持 (pytest-asyncio)
**目标平台**: Linux/macOS 服务器 (开发), 任何支持 Python asyncio 的平台
**项目类型**: 单一项目 - 扩展现有 Skill 系统
**性能目标**: 支持 50 个并发会话，响应时间 <30 秒
**约束**:
- 不破坏现有 Agent、CLI 功能
- FeishuSkill 可独立启用/禁用
- 通用框架支持未来扩展其他平台
**规模/范围**: 50 个并发用户，单实例部署

## 章程检查

*门禁: 必须在阶段 0 研究前通过。阶段 1 设计后重新检查。*

| 原则 | 状态 | 证据 |
|------|------|------|
| **I. 简洁优先** | ✅ 通过 | 通用长连接框架与具体平台实现分离。FeishuSkill 作为 Skill 注册，不修改核心逻辑。 |
| **II. 工具扩展性** | ✅ 通过 | 基于现有 Skill 系统扩展，新增 LongConnectionPlatform 接口。 |
| **III. 测试覆盖** | ✅ 通过 | 需要测试: 框架接口, 注册机制, FeishuSkill 连接/重连, 会话隔离。 |
| **IV. 智能上下文管理** | ✅ 通过 | 利用现有 Agent 上下文管理。每用户独立会话。 |
| **V. API 兼容性** | ✅ 通过 | 使用现有 LLMClient 抽象。不修改 LLM 层。 |
| **技术标准** | ✅ 通过 | Python 3.11+, pydantic 模型, 异步优先设计, 结构化日志。 |
| **配置层级** | ✅ 通过 | Feishu 配置通过 `feishu:` 节扩展现有 config.yaml。 |

**门禁状态**: ✅ 所有门禁通过

## 项目结构

### 文档 (本功能)

```text
specs/001-feishu-websocket-integration/
├── plan.md              # 本文件
├── research.md          # 阶段 0 输出
├── data-model.md        # 阶段 1 输出
├── quickstart.md        # 阶段 1 输出
├── contracts/           # 阶段 1 输出
│   └── feishu-events.md
└── tasks.md             # 阶段 2 输出 (/speckit.tasks)
```

### 源代码 (仓库根目录)

```text
mini_agent/
├── agent.py                     # 现有 - 添加事件处理器
├── cli.py                       # 现有 - 注册 Skills
├── skills/                      # 现有
│   └── feishu_skill/           # NEW: 飞书 Skill (可插拔)
│       ├── __init__.py         # Skill 入口，注册到 registry
│       ├── skill.yaml          # Skill 元数据
│       ├── config.py           # FeishuConfig
│       ├── ws_client.py        # FeishuWSClient - WebSocket 连接
│       ├── event_handler.py    # FeishuEventHandler - 解析事件
│       ├── message.py          # FeishuMessageSender - 发送回复
│       └── session_manager.py  # SessionManager - 每用户会话
└── long_connection/            # NEW: 通用长连接框架
    ├── __init__.py
    ├── base.py                # LongConnectionPlatform 抽象基类
    └── registry.py            # LongConnectionRegistry 注册中心

tests/
├── unit/
│   └── test_long_connection/  # NEW: 框架测试
│       ├── test_base.py
│       └── test_registry.py
│   └── test_feishu_skill/     # NEW: FeishuSkill 测试
│       ├── test_config.py
│       ├── test_session_manager.py
│       └── test_event_handler.py
└── integration/
    └── test_feishu_skill/     # NEW: 集成测试
        └── test_feishu_skill_service.py
```

**结构决策**: 在现有 Skill 系统基础上扩展。新增 `long_connection/` 通用框架，`feishu_skill/` 作为具体平台实现位于 `skills/` 目录下。

## 复杂度跟踪

> 无违规 - 设计遵循所有章程原则。

无需复杂度理由说明。
