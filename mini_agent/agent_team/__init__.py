"""
Agent Team - Multi-agent chatroom for collaborative discussions

Supports multiple AI agents discussing the same topic with shared memory.
"""

import asyncio
import os
from enum import Enum
from typing import Optional
from dataclasses import dataclass

from mini_agent.agent_team.chatroom import Chatroom, ChatroomManager
from mini_agent.agent_team.agent import Agent, AgentConfig, ModelProvider
from mini_agent.agent_team.memory import Memory, Message
from mini_agent.agent_team.personality import Personality
from mini_agent.agent_team.providers import ProvidersConfig, ProviderConfig, PROVIDER_ENV_VARS


class DiscussionMode(str, Enum):
    """Discussion mode enumeration."""

    CONCURRENT = "concurrent"  # 所有 Agent 同时响应
    DEBATE = "debate"  # 串行辩论模式，一个一个发言


@dataclass
class AgentResponse:
    """Response from an agent."""

    agent_id: str
    agent_name: str
    content: str
    success: bool
    error: Optional[str] = None


class AgentTeam:
    """
    Main class for managing a multi-agent chatroom.

    Features:
    - Create and manage chatrooms
    - Add/remove agents with different models and personalities
    - All agents share the same memory
    - Two discussion modes: concurrent (parallel) or debate (serial)
    """

    def __init__(
        self,
        name: str,
        max_agents: int = 10,
        timeout: float = 30.0,
        providers_config: Optional[ProvidersConfig] = None,
        discussion_mode: DiscussionMode = DiscussionMode.CONCURRENT,
    ):
        """
        Initialize AgentTeam with a chatroom.

        Args:
            name: Chatroom name
            max_agents: Maximum number of agents
            timeout: Response timeout in seconds
            providers_config: Provider configuration (optional)
            discussion_mode: Discussion mode (concurrent or debate)
        """
        self._chatroom = Chatroom(name=name, max_members=max_agents)
        self._agents: dict[str, Agent] = {}
        self._timeout = timeout
        self._providers_config = providers_config
        self._discussion_mode = discussion_mode

    @property
    def chatroom(self) -> Chatroom:
        """Get the chatroom."""
        return self._chatroom

    @property
    def agents(self) -> dict[str, Agent]:
        """Get all agents."""
        return self._agents

    def _get_provider_info(self, provider_id: str) -> tuple[str, Optional[str], Optional[str]]:
        """
        Get API URL and key from provider config.

        Returns:
            (provider_type, api_url, api_key)
        """
        if not self._providers_config:
            # No config, return defaults
            return provider_id, None, None

        provider = self._providers_config.get_provider(provider_id)
        if not provider or not provider.enabled:
            return provider_id, None, None

        # Get API key from env var
        env_var = PROVIDER_ENV_VARS.get(provider_id)
        api_key = None
        if env_var:
            api_key = os.environ.get(env_var) or provider.api_key

        return provider_id, provider.api_url, api_key

    def add_agent(
        self,
        name: str,
        provider_id: str = "anthropic",
        model_name: str = "claude-sonnet-4-20250514",
        personality_name: str = "Assistant",
        system_prompt: str = "You are a helpful assistant.",
        response_style: Optional[str] = None,
    ) -> Agent:
        """
        Add an agent to the chatroom using provider_id.

        Args:
            name: Agent name
            provider_id: Provider ID (e.g., "anthropic", "openai", "deepseek")
            model_name: Model name (e.g., "claude-sonnet-4-20250514", "gpt-4")
            personality_name: Personality name
            system_prompt: System prompt
            response_style: Response style

        Returns:
            Created agent
        """
        if len(self._agents) >= self._chatroom.max_members:
            raise ValueError(f"Maximum number of agents ({self._chatroom.max_members}) reached")

        # Get provider info
        provider_type, api_url, api_key = self._get_provider_info(provider_id)

        # Map provider_id to ModelProvider enum
        provider_map = {
            "anthropic": ModelProvider.ANTHROPIC,
            "openai": ModelProvider.OPENAI,
            "deepseek": ModelProvider.OPENAI,  # DeepSeek compatible with OpenAI
            "bigmodel": ModelProvider.OPENAI,  # BigModel compatible with OpenAI
            "minimax": ModelProvider.OPENAI,  # MiniMax compatible with OpenAI
            "ollama": ModelProvider.OPENAI,  # Ollama compatible with OpenAI
            "lmstudio": ModelProvider.OPENAI,  # LM Studio compatible with OpenAI
            "custom": ModelProvider.CUSTOM,
        }
        model_provider = provider_map.get(provider_id, ModelProvider.OPENAI)

        # Create personality
        personality = Personality(
            name=personality_name,
            system_prompt=system_prompt,
            response_style=response_style,
        )

        # Create agent config
        config = AgentConfig(
            name=name,
            model_provider=model_provider,
            model_name=model_name,
            api_url=api_url,
            api_key=api_key,
            personality=personality,
        )

        # Create agent
        agent = Agent(config)
        self._agents[agent.id] = agent

        return agent

    # 兼容旧接口
    def add_agent_legacy(
        self,
        name: str,
        model_provider: str = "anthropic",
        model_name: str = "claude-sonnet-4-20250514",
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        personality_name: str = "Assistant",
        system_prompt: str = "You are a helpful assistant.",
        response_style: Optional[str] = None,
    ) -> Agent:
        """Legacy add_agent method with full parameters."""
        if len(self._agents) >= self._chatroom.max_members:
            raise ValueError(f"Maximum number of agents ({self._chatroom.max_members}) reached")

        # Map to ModelProvider enum
        provider_map = {
            "anthropic": ModelProvider.ANTHROPIC,
            "openai": ModelProvider.OPENAI,
            "custom": ModelProvider.CUSTOM,
        }
        provider_enum = provider_map.get(model_provider, ModelProvider.OPENAI)

        personality = Personality(
            name=personality_name,
            system_prompt=system_prompt,
            response_style=response_style,
        )

        config = AgentConfig(
            name=name,
            model_provider=provider_enum,
            model_name=model_name,
            api_url=api_url,
            api_key=api_key,
            personality=personality,
        )

        agent = Agent(config)
        self._agents[agent.id] = agent
        return agent

    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the chatroom.

        Args:
            agent_id: Agent ID

        Returns:
            True if removed, False if not found
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[Agent]:
        """List all agents."""
        return list(self._agents.values())

    async def discuss(self, topic: str, add_topic_to_memory: bool = True) -> list[AgentResponse]:
        """
        Start a discussion on a topic.

        Args:
            topic: Discussion topic
            add_topic_to_memory: Whether to add topic as user message to memory.
                                Set False for subsequent rounds on the same topic.

        Returns:
            List of agent responses
        """
        if add_topic_to_memory:
            self._chatroom.memory.add_message(role="user", content=topic)

        if self._discussion_mode == DiscussionMode.DEBATE:
            return await self._discuss_debate()
        else:
            return await self._discuss_concurrent()

    async def _discuss_concurrent(self) -> list[AgentResponse]:
        """
        Concurrent discussion mode - all agents respond simultaneously.

        Each agent gets its own view of messages (with self-identification).

        Returns:
            List of agent responses
        """
        # Create tasks for all agents, each with its own message view
        tasks = []
        active_agents = []
        for agent in self._agents.values():
            if agent.is_active:
                messages = self._chatroom.memory.get_messages_for_agent(
                    current_agent_name=agent.name
                )
                tasks.append(self._call_agent(agent, messages))
                active_agents.append(agent)

        # Wait for all responses
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        results = []
        for i, response in enumerate(responses):
            if i >= len(active_agents):
                continue
            agent = active_agents[i]
            if isinstance(response, Exception):
                results.append(AgentResponse(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content="",
                    success=False,
                    error=str(response),
                ))
            else:
                results.append(AgentResponse(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response,
                    success=True,
                ))

                # Add agent response to memory
                self._chatroom.memory.add_message(
                    role="agent",
                    content=response,
                    agent_id=agent.id,
                    agent_name=agent.name,
                )

        return results

    async def _discuss_debate(self) -> list[AgentResponse]:
        """
        Debate mode - agents respond one by one, seeing each other's responses.

        Each agent responds sequentially, and their response is added to memory
        before the next agent responds. This allows for true debate.

        Returns:
            List of agent responses
        """
        results = []

        # Get active agents in order
        agent_list = [agent for agent in self._agents.values() if agent.is_active]

        # Each agent responds one by one
        for agent in agent_list:
            # Get current memory context with agent identity
            messages = self._chatroom.memory.get_messages_for_agent(
                current_agent_name=agent.name
            )

            try:
                # Call agent
                response = await asyncio.wait_for(
                    agent.generate_response(messages),
                    timeout=self._timeout
                )

                results.append(AgentResponse(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response,
                    success=True,
                ))

                # Add response to memory immediately so next agent sees it
                self._chatroom.memory.add_message(
                    role="agent",
                    content=response,
                    agent_id=agent.id,
                    agent_name=agent.name,
                )

            except asyncio.TimeoutError:
                results.append(AgentResponse(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content="",
                    success=False,
                    error=f"Timeout after {self._timeout}s",
                ))
            except Exception as e:
                results.append(AgentResponse(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content="",
                    success=False,
                    error=str(e),
                ))

        return results

    async def _call_agent(self, agent: Agent, messages: list[dict]) -> str:
        """
        Call an agent with timeout.

        Args:
            agent: Agent to call
            messages: Messages for context

        Returns:
            Agent response
        """
        try:
            return await asyncio.wait_for(
                agent.generate_response(messages),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Agent {agent.name} timed out after {self._timeout}s")


def load_providers_from_config(config_path: str = "mini_agent/config/config.yaml") -> Optional[ProvidersConfig]:
    """Load providers configuration from config.yaml."""
    try:
        import yaml
        with open(config_path) as f:
            data = yaml.safe_load(f)

        agent_team_config = data.get("agent_team", {})
        providers_data = agent_team_config.get("providers", {})

        if not providers_data:
            print(f"Warning: No providers data found in {config_path}")
            return None

        providers = ProvidersConfig()
        for name, config in providers_data.items():
            if hasattr(providers, name):
                provider_config = ProviderConfig(
                    enabled=config.get("enabled", False),
                    api_url=config.get("api_url", ""),
                    api_key=config.get("api_key"),
                )
                setattr(providers, name, provider_config)

        return providers
    except Exception as e:
        print(f"Error loading providers from {config_path}: {e}")
        import traceback
        traceback.print_exc()
        return None


@dataclass
class AgentTeamConfig:
    """Agent Team configuration from config.yaml."""

    discussion_mode: DiscussionMode = DiscussionMode.DEBATE
    timeout: float = 30.0
    max_agents: int = 10
    providers_config: Optional[ProvidersConfig] = None


def load_agent_team_config(config_path: str = "mini_agent/config/config.yaml") -> AgentTeamConfig:
    """Load full agent team configuration from config.yaml."""
    try:
        import yaml
        with open(config_path) as f:
            data = yaml.safe_load(f)

        agent_team_config = data.get("agent_team", {})

        # Load discussion mode
        mode_str = agent_team_config.get("discussion_mode", "debate")
        discussion_mode = DiscussionMode.CONCURRENT if mode_str == "concurrent" else DiscussionMode.DEBATE

        # Load timeout
        timeout = agent_team_config.get("default_timeout", 30.0)

        # Load max agents
        max_agents = agent_team_config.get("max_agents_per_chatroom", 10)

        # Load providers
        providers_config = load_providers_from_config(config_path)

        return AgentTeamConfig(
            discussion_mode=discussion_mode,
            timeout=timeout,
            max_agents=max_agents,
            providers_config=providers_config,
        )
    except Exception as e:
        print(f"Error loading agent team config from {config_path}: {e}")
        # Return defaults
        return AgentTeamConfig()
