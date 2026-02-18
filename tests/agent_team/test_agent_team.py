"""
Agent Team 自动化测试

测试聊天室创建、Agent 配置、共享 Memory、协同讨论等功能。
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_agent.agent_team import AgentTeam, Agent, Chatroom, Memory, Personality, AgentConfig, ModelProvider
from mini_agent.agent_team.memory import Message


class TestResult:
    """测试结果收集器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def add_fail(self, name, error):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  ❌ {name}: {error}")

    def summary(self):
        print(f"\n{'='*50}")
        print(f"测试结果: {self.passed} 通过, {self.failed} 失败")
        print(f"{'='*50}")
        if self.errors:
            print("\n失败详情:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        return self.failed == 0


# ========== Phase 1: 基础模型测试 ==========

async def test_personality_model(result: TestResult):
    """测试 Personality 模型"""
    print("\n[测试 1] Personality 模型")

    try:
        personality = Personality(
            name="专业冷静",
            system_prompt="你是一个专业的技术顾问。",
            response_style="简洁专业"
        )
        if personality.name == "专业冷静" and personality.system_prompt:
            result.add_pass("Personality 创建")
        else:
            result.add_fail("Personality 创建", "属性不匹配")
    except Exception as e:
        result.add_fail("Personality 创建", str(e))

    try:
        personality = Personality(
            name="测试",
            system_prompt="短提示"
        )
        if personality.response_style is None:
            result.add_pass("可选字段默认值为空")
        else:
            result.add_fail("可选字段默认值", "应该为 None")
    except Exception as e:
        result.add_fail("可选字段默认值", str(e))


async def test_message_model(result: TestResult):
    """测试 Message 模型"""
    print("\n[测试 2] Message 模型")

    try:
        msg = Message(
            id="test-123",
            role="user",
            content="你好",
            agent_id=None,
            agent_name=None
        )
        if msg.role == "user" and msg.content == "你好":
            result.add_pass("Message 创建")
        else:
            result.add_fail("Message 创建", "属性不匹配")
    except Exception as e:
        result.add_fail("Message 创建", str(e))

    try:
        msg = Message(
            role="agent",
            content="回复内容",
            agent_id="agent-1",
            agent_name="Claude"
        )
        if msg.agent_id == "agent-1" and msg.agent_name == "Claude":
            result.add_pass("Agent Message 创建")
        else:
            result.add_fail("Agent Message 创建", "属性不匹配")
    except Exception as e:
        result.add_fail("Agent Message 创建", str(e))


async def test_memory_model(result: TestResult):
    """测试 Memory 模型"""
    print("\n[测试 3] Memory 模型")

    try:
        memory = Memory()
        msg = memory.add_message(role="user", content="测试消息")
        if len(memory.messages) == 1:
            result.add_pass("Memory 添加消息")
        else:
            result.add_fail("Memory 添加消息", "消息未添加")
    except Exception as e:
        result.add_fail("Memory 添加消息", str(e))

    try:
        memory = Memory()
        memory.add_message(role="user", content="消息1")
        memory.add_message(role="agent", content="回复1")
        msgs = memory.get_messages()
        if len(msgs) == 2:
            result.add_pass("Memory 获取消息列表")
        else:
            result.add_fail("Memory 获取消息列表", f"期望2个，实际{len(msgs)}")
    except Exception as e:
        result.add_fail("Memory 获取消息列表", str(e))

    try:
        memory = Memory()
        memory.add_message(role="user", content="测试")
        memory.clear()
        if len(memory.messages) == 0:
            result.add_pass("Memory 清空")
        else:
            result.add_fail("Memory 清空", "未清空")
    except Exception as e:
        result.add_fail("Memory 清空", str(e))

    try:
        memory = Memory()
        memory.add_message(role="user", content="消息1")
        memory.add_message(role="user", content="消息2")
        formatted = memory.get_messages_for_agent()
        if len(formatted) == 2 and formatted[0]["role"] == "user":
            result.add_pass("Memory 格式化输出")
        else:
            result.add_fail("Memory 格式化输出", "格式错误")
    except Exception as e:
        result.add_fail("Memory 格式化输出", str(e))


async def test_agent_config_model(result: TestResult):
    """测试 AgentConfig 模型"""
    print("\n[测试 4] AgentConfig 模型")

    try:
        personality = Personality(name="测试", system_prompt="提示词")
        config = AgentConfig(
            name="TestAgent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-sonnet-4-20250514",
            personality=personality
        )
        if config.name == "TestAgent" and config.model_provider == ModelProvider.ANTHROPIC:
            result.add_pass("AgentConfig 创建")
        else:
            result.add_fail("AgentConfig 创建", "属性不匹配")
    except Exception as e:
        result.add_fail("AgentConfig 创建", str(e))

    try:
        config = AgentConfig(
            name="CustomAgent",
            model_provider=ModelProvider.CUSTOM,
            model_name="local-model",
            api_url="http://localhost:8000",
            personality=Personality(name="测试", system_prompt="提示")
        )
        if config.api_url == "http://localhost:8000":
            result.add_pass("自定义 API URL")
        else:
            result.add_fail("自定义 API URL", "未设置")
    except Exception as e:
        result.add_fail("自定义 API URL", str(e))


async def test_chatroom_model(result: TestResult):
    """测试 Chatroom 模型"""
    print("\n[测试 5] Chatroom 模型")

    try:
        chatroom = Chatroom(name="测试聊天室")
        if chatroom.name == "测试聊天室" and chatroom.max_members == 10:
            result.add_pass("Chatroom 创建")
        else:
            result.add_fail("Chatroom 创建", "属性不匹配")
    except Exception as e:
        result.add_fail("Chatroom 创建", str(e))

    try:
        chatroom = Chatroom(name="测试", max_members=5)
        if chatroom.max_members == 5:
            result.add_pass("自定义最大成员数")
        else:
            result.add_fail("自定义最大成员数", "未生效")
    except Exception as e:
        result.add_fail("自定义最大成员数", str(e))

    try:
        chatroom = Chatroom(name="测试")
        msg = chatroom.memory.add_message(role="user", content="测试")
        if len(chatroom.memory.messages) == 1:
            result.add_pass("Chatroom 内置 Memory")
        else:
            result.add_fail("Chatroom 内置 Memory", "未初始化")
    except Exception as e:
        result.add_fail("Chatroom 内置 Memory", str(e))


# ========== Phase 2: AgentTeam 功能测试 ==========

async def test_agent_team_creation(result: TestResult):
    """测试 AgentTeam 创建"""
    print("\n[测试 6] AgentTeam 创建")

    try:
        team = AgentTeam(name="技术评审", max_agents=5, timeout=10.0)
        if team.chatroom.name == "技术评审" and team.chatroom.max_members == 5:
            result.add_pass("AgentTeam 创建")
        else:
            result.add_fail("AgentTeam 创建", "属性不匹配")
    except Exception as e:
        result.add_fail("AgentTeam 创建", str(e))

    try:
        team = AgentTeam(name="测试", max_agents=3)
        agents = team.list_agents()
        if len(agents) == 0:
            result.add_pass("初始无 Agent")
        else:
            result.add_fail("初始无 Agent", "应该为空")
    except Exception as e:
        result.add_fail("初始无 Agent", str(e))


async def test_add_agent(result: TestResult):
    """测试添加 Agent"""
    print("\n[测试 7] 添加 Agent")

    try:
        team = AgentTeam(name="测试")
        agent = team.add_agent(
            name="Claude专家",
            provider_id="anthropic",
            model_name="claude-sonnet-4-20250514",
            personality_name="专业冷静",
            system_prompt="你是一个专业顾问。"
        )
        if agent.name == "Claude专家" and agent.is_active:
            result.add_pass("添加 Agent")
        else:
            result.add_fail("添加 Agent", "属性错误")
    except Exception as e:
        result.add_fail("添加 Agent", str(e))

    try:
        team = AgentTeam(name="测试")
        team.add_agent(name="Agent1", provider_id="anthropic", model_name="claude", system_prompt="提示")
        team.add_agent(name="Agent2", provider_id="openai", model_name="gpt-4", system_prompt="提示")
        agents = team.list_agents()
        if len(agents) == 2:
            result.add_pass("添加多个 Agent")
        else:
            result.add_fail("添加多个 Agent", f"期望2，实际{len(agents)}")
    except Exception as e:
        result.add_fail("添加多个 Agent", str(e))

    try:
        team = AgentTeam(name="测试", max_agents=2)
        team.add_agent(name="A1", provider_id="anthropic", model_name="claude", system_prompt="提示")
        team.add_agent(name="A2", provider_id="anthropic", model_name="claude", system_prompt="提示")
        try:
            team.add_agent(name="A3", provider_id="anthropic", model_name="claude", system_prompt="提示")
            result.add_fail("最大成员数限制", "应该抛出异常")
        except ValueError:
            result.add_pass("最大成员数限制")
    except Exception as e:
        result.add_fail("最大成员数限制", str(e))


async def test_remove_agent(result: TestResult):
    """测试移除 Agent"""
    print("\n[测试 8] 移除 Agent")

    try:
        team = AgentTeam(name="测试")
        agent = team.add_agent(name="Test", provider_id="anthropic", model_name="claude", system_prompt="提示")
        agent_id = agent.id
        removed = team.remove_agent(agent_id)
        if removed and len(team.list_agents()) == 0:
            result.add_pass("移除 Agent")
        else:
            result.add_fail("移除 Agent", "未正确移除")
    except Exception as e:
        result.add_fail("移除 Agent", str(e))

    try:
        team = AgentTeam(name="测试")
        team.add_agent(name="Test", provider_id="anthropic", model_name="claude", system_prompt="提示")
        removed = team.remove_agent("不存在的ID")
        if not removed:
            result.add_pass("移除不存在的 Agent")
        else:
            result.add_fail("移除不存在的 Agent", "应该返回 False")
    except Exception as e:
        result.add_fail("移除不存在的 Agent", str(e))


async def test_shared_memory(result: TestResult):
    """测试共享 Memory"""
    print("\n[测试 9] 共享 Memory")

    try:
        team = AgentTeam(name="测试")
        team.add_agent(name="A1", provider_id="anthropic", model_name="claude", system_prompt="提示")
        team.add_agent(name="A2", provider_id="anthropic", model_name="claude", system_prompt="提示")

        # 添加用户消息
        team.chatroom.memory.add_message(role="user", content="你好")

        # 两个 Agent 都能看到
        msgs = team.chatroom.memory.get_messages()
        if len(msgs) == 1 and msgs[0].content == "你好":
            result.add_pass("共享 Memory - 用户消息")
        else:
            result.add_fail("共享 Memory - 用户消息", "消息未同步")
    except Exception as e:
        result.add_fail("共享 Memory - 用户消息", str(e))

    try:
        team = AgentTeam(name="测试")
        team.add_agent(name="A1", provider_id="anthropic", model_name="claude", system_prompt="提示")

        # 添加 Agent 消息
        team.chatroom.memory.add_message(
            role="agent",
            content="我是 Agent A1",
            agent_id="test-agent",
            agent_name="A1"
        )

        msgs = team.chatroom.memory.get_messages_for_agent()
        if len(msgs) == 1:
            result.add_pass("共享 Memory - Agent 消息")
        else:
            result.add_fail("共享 Memory - Agent 消息", "消息格式错误")
    except Exception as e:
        result.add_fail("共享 Memory - Agent 消息", str(e))

    try:
        team = AgentTeam(name="测试")
        team.chatroom.memory.add_message(role="user", content="消息1")
        team.chatroom.memory.add_message(role="user", content="消息2")

        # 新 Agent 加入能看到历史
        team.add_agent(name="NewAgent", provider_id="anthropic", model_name="claude", system_prompt="提示")

        msgs = team.chatroom.memory.get_messages()
        if len(msgs) == 2:
            result.add_pass("新 Agent 看到历史消息")
        else:
            result.add_fail("新 Agent 看到历史消息", f"期望2，实际{len(msgs)}")
    except Exception as e:
        result.add_fail("新 Agent 看到历史消息", str(e))

    try:
        team = AgentTeam(name="测试")
        team.chatroom.memory.add_message(role="user", content="消息")
        team.chatroom.memory.clear()

        if team.chatroom.memory.count() == 0:
            result.add_pass("清空 Memory")
        else:
            result.add_fail("清空 Memory", "未清空")
    except Exception as e:
        result.add_fail("清空 Memory", str(e))


async def test_model_provider_enum(result: TestResult):
    """测试 ModelProvider 枚举"""
    print("\n[测试 10] ModelProvider 枚举")

    try:
        if ModelProvider.OPENAI.value == "openai":
            result.add_pass("OPENAI 枚举值")
        else:
            result.add_fail("OPENAI 枚举值", "值错误")
    except Exception as e:
        result.add_fail("OPENAI 枚举值", str(e))

    try:
        if ModelProvider.ANTHROPIC.value == "anthropic":
            result.add_pass("ANTHROPIC 枚举值")
        else:
            result.add_fail("ANTHROPIC 枚举值", "值错误")
    except Exception as e:
        result.add_fail("ANTHROPIC 枚举值", str(e))

    try:
        if ModelProvider.CUSTOM.value == "custom":
            result.add_pass("CUSTOM 枚举值")
        else:
            result.add_fail("CUSTOM 枚举值", "值错误")
    except Exception as e:
        result.add_fail("CUSTOM 枚举值", str(e))


async def test_agent_activation(result: TestResult):
    """测试 Agent 激活/停用"""
    print("\n[测试 11] Agent 激活状态")

    try:
        team = AgentTeam(name="测试")
        agent = team.add_agent(name="Test", provider_id="anthropic", model_name="claude", system_prompt="提示")

        if agent.is_active:
            result.add_pass("默认激活状态")
        else:
            result.add_fail("默认激活状态", "应该默认激活")
    except Exception as e:
        result.add_fail("默认激活状态", str(e))

    try:
        team = AgentTeam(name="测试")
        agent = team.add_agent(name="Test", provider_id="anthropic", model_name="claude", system_prompt="提示")
        agent.deactivate()

        if not agent.is_active:
            result.add_pass("停用 Agent")
        else:
            result.add_fail("停用 Agent", "未停用")
    except Exception as e:
        result.add_fail("停用 Agent", str(e))

    try:
        team = AgentTeam(name="测试")
        agent = team.add_agent(name="Test", provider_id="anthropic", model_name="claude", system_prompt="提示")
        agent.deactivate()
        agent.activate()

        if agent.is_active:
            result.add_pass("重新激活 Agent")
        else:
            result.add_fail("重新激活 Agent", "未激活")
    except Exception as e:
        result.add_fail("重新激活 Agent", str(e))


async def test_get_agent_methods(result: TestResult):
    """测试获取 Agent 方法"""
    print("\n[测试 12] 获取 Agent 方法")

    try:
        team = AgentTeam(name="测试")
        agent = team.add_agent(name="TestAgent", provider_id="anthropic", model_name="claude", system_prompt="提示")

        retrieved = team.get_agent(agent.id)
        if retrieved and retrieved.name == "TestAgent":
            result.add_pass("get_agent 方法")
        else:
            result.add_fail("get_agent 方法", "未找到")
    except Exception as e:
        result.add_fail("get_agent 方法", str(e))

    try:
        team = AgentTeam(name="测试")
        team.add_agent(name="Agent1", provider_id="anthropic", model_name="claude", system_prompt="提示")
        team.add_agent(name="Agent2", provider_id="anthropic", model_name="claude", system_prompt="提示")

        agents = team.list_agents()
        if len(agents) == 2:
            result.add_pass("list_agents 方法")
        else:
            result.add_fail("list_agents 方法", f"期望2，实际{len(agents)}")
    except Exception as e:
        result.add_fail("list_agents 方法", str(e))


# ========== 主函数 ==========

async def main():
    """主测试函数"""
    print("="*50)
    print("Agent Team 自动化测试")
    print("="*50)

    result = TestResult()

    # Phase 1: 基础模型测试
    await test_personality_model(result)
    await test_message_model(result)
    await test_memory_model(result)
    await test_agent_config_model(result)
    await test_chatroom_model(result)

    # Phase 2: AgentTeam 功能测试
    await test_agent_team_creation(result)
    await test_add_agent(result)
    await test_remove_agent(result)
    await test_shared_memory(result)
    await test_model_provider_enum(result)
    await test_agent_activation(result)
    await test_get_agent_methods(result)

    # 输出结果
    success = result.summary()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
