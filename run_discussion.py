#!/usr/bin/env python3
"""
Agent Team 讨论脚本

使用方法:
    python run_discussion.py --topic "你的话题" --rounds 3

Agent 配置从 mini_agent/agents/agents.yaml 加载。
性格模板从 mini_agent/agents/personalities/ 加载。
"""

import asyncio
import argparse
from typing import Optional
from mini_agent.agent_team import AgentTeam, load_agent_team_config, DiscussionMode
from mini_agent.agents import AgentConfigLoader


# ============================================================
# Legacy Agent 配置 (仅在 agents.yaml 不存在时使用)
# ============================================================

def create_agent_config(
    name: str,
    provider_id: str,
    model_name: str = "claude-sonnet-4-20250514",
    personality_name: str = "Assistant",
    system_prompt: str = "You are a helpful assistant.",
    response_style: Optional[str] = None,
) -> dict:
    """创建 Agent 配置 (legacy)"""
    return {
        "name": name,
        "provider_id": provider_id,
        "model_name": model_name,
        "personality_name": personality_name,
        "system_prompt": system_prompt,
        "response_style": response_style,
    }


LEGACY_AGENTS = [
    create_agent_config(
        name="deepseek专家",
        provider_id="deepseek",
        model_name="deepseek-chat",
        personality_name="专业冷静",
        system_prompt="你是一个资深技术专家。回答问题时保持客观理性，给出具体可执行的建议。"
    ),
    # create_agent_config(
    #     name="智谱助手",
    #     provider_id="bigmodel",
    #     model_name="glm-5",
    #     personality_name="中文专家",
    #     system_prompt="你是一个中文AI助手，擅长中文对话。"
    # ),
    create_agent_config(
        name="MiniMax专家",
        provider_id="minimax",
        model_name="MiniMax-M2.5",
        personality_name="全能助手",
        system_prompt="你是一个全能的AI助手。"
    ),
    # create_agent_config(
    #     name="lmstudio",
    #     provider_id="lmstudio",
    #     model_name="glm-4.7-flash",
    #     personality_name="本地助手",
    #     system_prompt="你是一个本地部署的AI助手。"
    # ),
]


# ============================================================
# 默认配置
# ============================================================

DEFAULT_TOPIC = "如何设计一个高并发的分布式系统?"
DEFAULT_ROUNDS = 1
DEFAULT_DISCUSSION_MODE = DiscussionMode.DEBATE

PROVIDER_MODEL_HINTS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4",
    "deepseek": "deepseek-chat",
    "bigmodel": "glm-5",
    "minimax": "abab6.5s-chat",
    "ollama": "qwen2.5",
    "lmstudio": "glm-4.7-flash",
    "custom": "qwen2.5",
}


async def run_discussion(topic: str, rounds: int, mode: str, config_path: str = None):
    """运行讨论

    Args:
        topic: 讨论话题
        rounds: 讨论回合数
        mode: 讨论模式 (concurrent 或 debate)
        config_path: 配置文件路径 (可选)
    """
    # Parse mode
    discussion_mode = DiscussionMode.CONCURRENT if mode == "concurrent" else DiscussionMode.DEBATE

    # 从配置文件加载 agent team 配置
    team_config = load_agent_team_config(config_path) if config_path else load_agent_team_config()

    # 尝试从 agents.yaml 加载 agent 定义
    loader = AgentConfigLoader()
    loader.load_personality_templates()
    agent_defs = loader.load_agents()

    # 确定 agent 数量
    agent_count = len(agent_defs) if agent_defs else len(LEGACY_AGENTS)

    print("=" * 60)
    print("Agent Team 讨论程序")
    print("=" * 60)
    print(f"话题: {topic}")
    print(f"回合数: {rounds}")
    print(f"讨论模式: {'并发 (concurrent)' if mode == 'concurrent' else '辩论 (debate)'}")
    print(f"Agent 数量: {agent_count}")
    print(f"配置来源: {'agents.yaml' if agent_defs else 'legacy (硬编码)'}")
    print("-" * 60)

    # 创建聊天室
    team = AgentTeam(
        name="讨论室",
        max_agents=agent_count,
        timeout=team_config.timeout if team_config else 60.0,
        providers_config=team_config.providers_config if team_config else None,
        discussion_mode=discussion_mode,
    )

    # 添加 Agent
    print("\n添加 Agent:")
    if agent_defs:
        # 从 agents.yaml 加载
        for agent_def in agent_defs:
            personality = loader.resolve_personality(agent_def)
            agent = team.add_agent(
                name=agent_def.name,
                provider_id=agent_def.provider_id,
                model_name=agent_def.model_name,
                personality_name=personality.name,
                system_prompt=personality.system_prompt,
                response_style=personality.response_style,
            )
            print(f"  - {agent.name} (provider={agent_def.provider_id}, model={agent_def.model_name}, personality={personality.name})")
    else:
        # Legacy fallback
        print("  (使用 legacy 配置)")
        for config in LEGACY_AGENTS:
            agent = team.add_agent(
                name=config["name"],
                provider_id=config["provider_id"],
                model_name=config.get("model_name", PROVIDER_MODEL_HINTS.get(config["provider_id"], "claude-sonnet-4-20250514")),
                personality_name=config["personality_name"],
                system_prompt=config["system_prompt"],
                response_style=config.get("response_style"),
            )
            print(f"  - {agent.name} (provider={config['provider_id']}, model={agent.config.model_name})")

    # 开始讨论
    print("\n" + "=" * 60)
    print("开始讨论")
    print("=" * 60)

    for round_num in range(1, rounds + 1):
        print(f"\n【第 {round_num} 轮讨论】")
        print(f"话题: {topic}")
        print("-" * 60)

        # 只在第一轮添加话题到记忆
        results = await team.discuss(topic, add_topic_to_memory=(round_num == 1))

        # 打印每个 Agent 的回复
        for r in results:
            print(f"\n--- {r.agent_name} ---")
            if r.success:
                print(r.content)
            else:
                print(f"错误: {r.error}")

        print("\n" + "-" * 60)
        print(f"本轮结束。共享记忆消息数: {team.chatroom.memory.count()}")

    # 总结
    print("\n" + "=" * 60)
    print("讨论结束")
    print("=" * 60)
    print(f"总回合数: {rounds}")
    print(f"总消息数: {team.chatroom.memory.count()}")
    print("\n完整对话历史:")
    for msg in team.chatroom.memory.messages:
        if msg.role == "user":
            print(f"  [用户]: {msg.content[:50]}...")
        else:
            print(f"  [{msg.agent_name}]: {msg.content[:50]}...")


def main():
    parser = argparse.ArgumentParser(description="Agent Team 讨论脚本")
    parser.add_argument("--topic", type=str, default=DEFAULT_TOPIC, help="讨论话题")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="讨论回合数")
    parser.add_argument("--mode", type=str, default=DEFAULT_DISCUSSION_MODE.value,
                        choices=["concurrent", "debate"], help="讨论模式: concurrent(并发) 或 debate(辩论串行)")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径 (默认: mini_agent/config/config.yaml)")
    parser.add_argument("--list-agents", action="store_true", help="列出预配置的 Agent")
    args = parser.parse_args()

    if args.list_agents:
        loader = AgentConfigLoader()
        loader.load_personality_templates()
        agent_defs = loader.load_agents()
        if agent_defs:
            print("配置的 Agent (agents.yaml):")
            for i, agent_def in enumerate(agent_defs, 1):
                p = agent_def.personality
                p_name = p if isinstance(p, str) else p.name
                print(f"  {i}. {agent_def.name} (provider={agent_def.provider_id}, model={agent_def.model_name}, personality={p_name})")
        else:
            print("Legacy 配置的 Agent:")
            for i, config in enumerate(LEGACY_AGENTS, 1):
                print(f"  {i}. {config['name']} (provider={config['provider_id']}, model={config['model_name']})")
        return

    asyncio.run(run_discussion(args.topic, args.rounds, args.mode, args.config))


if __name__ == "__main__":
    main()
