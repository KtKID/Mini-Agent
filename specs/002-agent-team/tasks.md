# Tasks: Agent Team 多智能体聊天室

**Feature**: Agent Team 多智能体聊天室
**Branch**: 002-agent-team
**Generated**: 2026-02-18

## 任务概览

- **总任务数**: 24
- **用户故事数**: 5
- **并行机会**: 4

## 依赖关系

```
US1 (聊天室创建)
  └─> US2 (Agent 配置)
        └─> US3 (协同讨论)
              └─> US4 (共享 Memory)
                    └─> US5 (动态管理)
```

## Phase 1: Setup (项目初始化)

- [x] T001 Create agent_team directory structure in mini_agent/
- [x] T002 Initialize __init__.py with module exports
- [x] T003 Add agent_team config to config.yaml

## Phase 2: Foundational (基础组件)

- [x] T004 [P] Create Personality model in mini_agent/agent_team/personality.py
- [x] T005 [P] Create Message model in mini_agent/agent_team/memory.py
- [x] T006 Create Memory model in mini_agent/agent_team/memory.py
- [x] T007 Create AgentConfig model in mini_agent/agent_team/agent.py
- [x] T008 Create Chatroom model in mini_agent/agent_team/chatroom.py
- [x] T009 Create AgentTeam main class in mini_agent/agent_team/__init__.py

## Phase 3: US1 - 创建聊天室并邀请 Agent (P1)

**目标**: 创建聊天室并添加 Agent
**独立测试**: 创建聊天室，添加 Agent，验证 Agent 列表

- [x] T010 [US1] Implement chatroom creation with unique ID in mini_agent/agent_team/chatroom.py
- [x] T011 [US1] Implement add_agent method in mini_agent/agent_team/chatroom.py
- [x] T012 [US1] Implement list_agents method in mini_agent/agent_team/chatroom.py
- [x] T013 [US1] Test chatroom creation and agent invitation

## Phase 4: US2 - Agent 配置不同模型和性格 (P1)

**目标**: 配置 Agent 的模型提供商和性格
**独立测试**: 创建配置好的 Agent，验证模型和性格

- [x] T014 [P] [US2] Implement ModelProvider enum in mini_agent/agent_team/agent.py
- [x] T015 [US2] Implement Agent initialization with model config in mini_agent/agent_team/agent.py
- [x] T016 [US2] Implement personality loading in mini_agent/agent_team/personality.py
- [x] T017 [US2] Test Agent configuration with different models and personalities

## Phase 5: US3 - 多 Agent 协同讨论 (P1)

**目标**: 多个 Agent 响应同一话题
**独立测试**: 发起讨论，验证所有 Agent 都响应

- [x] T018 [P] [US3] Implement LLM client wrapper reuse in mini_agent/agent_team/agent.py
- [x] T019 [US3] Implement concurrent agent response in mini_agent/agent_team/__init__.py
- [x] T020 [US3] Implement timeout handling in agent responses
- [x] T021 [US3] Implement error isolation for failed agents
- [x] T022 [US3] Test multi-agent discussion

## Phase 6: US4 - 共享 Memory (P1)

**目标**: 所有 Agent 共享对话历史
**独立测试**: Agent 能看到历史消息，理解上下文

- [x] T023 [US4] Implement message history in Memory in mini_agent/agent_team/memory.py
- [x] T024 [US4] Implement new agent sees history in mini_agent/agent_team/memory.py
- [x] T025 [US4] Implement clear memory in mini_agent/agent_team/memory.py
- [x] T026 [US4] Test shared memory functionality

## Phase 7: US5 - Agent 动态管理 (P2)

**目标**: 动态添加/移除 Agent
**独立测试**: 在讨论中添加/移除 Agent，不影响其他 Agent

- [x] T027 [P] [US5] Implement remove_agent method in mini_agent/agent_team/chatroom.py
- [x] T028 [US5] Implement update_agent_config method in mini_agent/agent_team/chatroom.py
- [x] T029 [US5] Test dynamic agent management

## Phase 8: Polish & Cross-Cutting (收尾)

- [x] T030 Add integration tests for full workflow
- [x] T031 Update README.md with usage examples
- [x] T032 Verify all tests pass

---

## 并行执行示例

### Phase 2 中的并行机会
- T004 (Personality) 和 T005 (Message) 可以并行执行

### Phase 4 中的并行机会
- T014 (ModelProvider) 和 T015 (Agent) 可以并行开发

---

## MVP 范围建议

**MVP**: 实现 User Story 1 + 3 + 4
- 聊天室创建和 Agent 添加
- 多 Agent 协同讨论
- 共享 Memory

**MVP 任务**: T001-T009, T010-T013, T018-T022, T023-T026
