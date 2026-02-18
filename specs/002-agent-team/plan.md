# Implementation Plan: Agent Team 多智能体聊天室

**Branch**: `002-agent-team` | **Date**: 2026-02-18 | **Spec**: specs/002-agent-team/spec.md
**Input**: Feature specification from `/specs/002-agent-team/spec.md`

## Summary

创建一个支持多智能体的聊天室架构，实现多个 AI Agent 在同一话题下协同讨论。每个 Agent 可配置不同的 AI 模型、API 端点和性格特征，所有 Agent 共享同一套 Memory。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: httpx, pydantic, asyncio (标准库), 复用现有 LLM 客户端
**Storage**: 内存存储（Session/Memory），可扩展为文件持久化
**Testing**: pytest with async support
**Target Platform**: Linux server, macOS
**Project Type**: CLI 工具扩展（基于现有 Mini-Agent）
**Performance Goals**: 支持 5+ Agent 同时讨论，单次响应延迟 < 10 秒
**Constraints**: 需要兼容 OpenAI/Anthropic 格式的 API
**Scale/Scope**: 单实例支持 10 个聊天室，每室 10 个 Agent

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Simplicity First | ✅ PASS | 复用现有 LLM 客户端，仅新增聊天室和 Agent 管理逻辑 |
| II. Tool Extensibility | ✅ PASS | Agent 作为可配置组件，符合扩展性原则 |
| III. Test Coverage | ✅ PASS | 需要为新功能编写测试 |
| IV. Context Management | ✅ PASS | 共享 Memory 设计符合上下文管理原则 |
| V. API Compatibility | ✅ PASS | 支持多模型 API 接入 |

## Project Structure

### Documentation (this feature)

```
specs/002-agent-team/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md            # Phase 2 output
```

### Source Code (repository root)

```
mini_agent/
├── agent.py             # 复用现有 Agent 核心
├── llm/                 # 复用现有 LLM 客户端
│   ├── llm_wrapper.py
│   ├── anthropic_client.py
│   └── openai_client.py
├── skills/              # 现有 Skills 目录
│   └── feishu_skill/   # 飞书 Skill (已存在)
└── NEW: agent_team/    # 新增: Agent Team 功能
    ├── __init__.py
    ├── chatroom.py     # 聊天室管理
    ├── agent.py        # Agent 配置和实例
    ├── memory.py       # 共享 Memory
    ├── personality.py  # 性格配置
    └── config.py       # 配置模型

tests/
├── test_agent_team/    # 新增测试
└── ...
```

**Structure Decision**: 在 `mini_agent/` 下新增 `agent_team/` 目录，实现聊天室和 Agent 管理功能。复用现有的 `llm/` 模块进行 AI 调用。

## Phase 0: Research

### 需要研究的问题

1. **多模型 API 统一封装**: 如何优雅地支持不同提供商的 API 调用
2. **共享 Memory 实现**: 聊天室中共享对话历史的最佳实践
3. **Agent 响应协调**: 多个 Agent 同时响应时的顺序和超时处理

### 决策

| 问题 | 决策 | 理由 |
|------|------|------|
| API 封装 | 复用现有 LLMClient | 保持一致性，减少重复代码 |
| Memory 存储 | 内存 + 可选文件持久化 | 简单优先，后续可扩展 |
| 响应协调 | 并发调用 + 超时控制 | 提高响应速度 |

## Complexity Tracking

本功能无复杂度违规。
