#!/usr/bin/env python3
"""
Agent Team 讨论脚本

使用方法:
    python run_discussion.py --topic "你的话题" --rounds 3

或在脚本中配置:
"""

import asyncio
import argparse
from typing import Optional
from mini_agent.agent_team import AgentTeam, load_providers_from_config


def create_agent_config(
    name: str,
    provider_id: str,
    model_name: str = "claude-sonnet-4-20250514",
    personality_name: str = "Assistant",
    system_prompt: str = "You are a helpful assistant.",
    response_style: Optional[str] = None,
) -> dict:
    """创建 Agent 配置

    Args:
        name: Agent 名称
        provider_id: Provider ID (anthropic, openai, deepseek, bigmodel, minimax, ollama, custom)
        model_name: 模型名称
        personality_name: 性格名称
        system_prompt: 系统提示词
        response_style: 回复风格 (可选)
    """
    return {
        "name": name,
        "provider_id": provider_id,
        "model_name": model_name,
        "personality_name": personality_name,
        "system_prompt": system_prompt,
        "response_style": response_style,
    }


# ============================================================
# 在这里配置你的 Agent 列表
# 只需要填写 provider_id (对应 config.yaml 中的 providers 配置)
# ============================================================

AGENTS = [
    # Agent 1: DeepSeek (使用 deepseek provider)
    create_agent_config(
        name="deepseek专家",
        provider_id="deepseek",
        model_name="deepseek-chat",
        personality_name="专业冷静",
        system_prompt="""你是一个资深技术专家。回答问题时:
- 保持客观理性，用数据说话
- 给出具体可执行的建议
- 遇到不确定的问题明确说明
- 回答简洁明了"""
    ),

    # Agent 2: OpenAI GPT (使用 openai provider)
#     create_agent_config(
#         name="OpenAI助手",
#         provider_id="openai",
#         model_name="gpt-5.2",
#         personality_name="热情友好",
#         system_prompt="""你是一个热情友好的助手。回答问题时:
# - 使用生动的例子帮助理解
# - 适当使用鼓励性语言
# - 鼓励用户继续提问
# - 回答亲切易懂"""
#     ),

    # Agent 3: DeepSeek (使用 deepseek provider)
    # create_agent_config(
    #     name="DeepSeek助手",
    #     provider_id="deepseek",
    #     model_name="deepseek-chat",
    #     personality_name="理性分析",
    #     system_prompt="""你是一个理性严谨的AI助手。回答问题时:
    # - 注重逻辑推理
    # - 提供深度分析
    # - 权衡利弊得失"""
    # ),

    # Agent 4: 智谱AI BigModel (使用 bigmodel provider)
    create_agent_config(
        name="智谱助手",
        provider_id="bigmodel",
        model_name="glm-5",
        personality_name="中文专家",
        system_prompt="你是一个中文AI助手，擅长中文对话。"
    ),

    # Agent 5: MiniMax (使用 minimax provider)
    create_agent_config(
        name="MiniMax专家",
        provider_id="minimax",
        model_name="MiniMax-M2.5",
        personality_name="全能助手",
        system_prompt="你是一个全能的AI助手。"
    ),

    # Agent 6: 本地模型 (使用 ollama 或 custom provider)
    # create_agent_config(
    #     name="本地模型",
    #     provider_id="ollama",  # 或 "custom"
    #     model_name="qwen2.5",  # 本地模型名称
    #     personality_name="本地助手",
    #     system_prompt="你是一个本地部署的AI助手。"
    # ),
    # Agent 6: LM Studio 本地模型 (使用 lmstudio provider)
    create_agent_config(
        name="lmstudio",
        provider_id="lmstudio",
        model_name="glm-4.7-flash",  # 本地模型名称
        personality_name="本地助手",
        system_prompt="你是一个本地部署的AI助手。"
    ),
]

# ============================================================
# 在这里配置讨论话题
# ============================================================

DEFAULT_TOPIC = "如何设计一个高并发的分布式系统?"

# ============================================================
# 在这里配置讨论回合数 (每回合所有 Agent 都会响应)
# ============================================================

DEFAULT_ROUNDS = 1


# Provider 模型名称映射 (可选配置，用于显示)
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


async def run_discussion(topic: str, rounds: int, config_path: str = None):
    """运行讨论

    Args:
        topic: 讨论话题
        rounds: 讨论回合数
        config_path: 配置文件路径 (可选)
    """
    print("=" * 60)
    print("Agent Team 讨论程序")
    print("=" * 60)
    print(f"话题: {topic}")
    print(f"回合数: {rounds}")
    print(f"Agent 数量: {len(AGENTS)}")
    print("-" * 60)

    # 从配置文件加载 providers
    providers_config = None
    if config_path:
        providers_config = load_providers_from_config(config_path)
    else:
        # 默认尝试加载项目配置
        providers_config = load_providers_from_config()

    if providers_config:
        print(f"已加载 providers 配置")
    else:
        print("警告: 未找到 providers 配置，将使用默认设置")

    # 创建聊天室
    team = AgentTeam(
        name="讨论室",
        max_agents=len(AGENTS),
        timeout=60.0,  # 超时时间(秒)
        providers_config=providers_config,
    )

    # 添加 Agent
    print("\n添加 Agent:")
    for config in AGENTS:
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

        results = await team.discuss(topic)

        # 打印每个 Agent 的回复
        for r in results:
            print(f"\n--- {r.agent_name} ---")
            if r.success:
                print(r.content)
            else:
                print(f"❌ 错误: {r.error}")

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
    parser.add_argument("--config", type=str, default=None, help="配置文件路径 (默认: mini_agent/config/config.yaml)")
    parser.add_argument("--list-agents", action="store_true", help="列出预配置的 Agent")
    args = parser.parse_args()

    if args.list_agents:
        print("预配置的 Agent:")
        for i, config in enumerate(AGENTS, 1):
            model = config.get("model_name", PROVIDER_MODEL_HINTS.get(config["provider_id"], ""))
            print(f"  {i}. {config['name']} (provider={config['provider_id']}, model={model})")
        return

    asyncio.run(run_discussion(args.topic, args.rounds, args.config))


if __name__ == "__main__":
    main()
