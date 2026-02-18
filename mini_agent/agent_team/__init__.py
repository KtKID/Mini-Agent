"""
Agent Team - Multi-agent chatroom for collaborative discussions

Supports multiple AI agents discussing the same topic with shared memory.
"""

import asyncio
import os
from typing import Optional
from dataclasses import dataclass

from mini_agent.agent_team.chatroom import Chatroom, ChatroomManager
from mini_agent.agent_team.agent import Agent, AgentConfig, ModelProvider
from mini_agent.agent_team.memory import Memory, Message
from mini_agent.agent_team.personality import Personality
from mini_agent.agent_team.providers import ProvidersConfig, ProviderConfig, PROVIDER_ENV_VARS


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
    - Concurrent agent responses with timeout handling
    """

    def __init__(
        self,
        name: str,
        max_agents: int = 10,
        timeout: float = 30.0,
        providers_config: Optional[ProvidersConfig] = None,
    ):
        """
        Initialize AgentTeam with a chatroom.

        Args:
            name: Chatroom name
            max_agents: Maximum number of agents
            timeout: Response timeout in seconds
            providers_config: Provider configuration (optional)
        """
        self._chatroom = Chatroom(name=name, max_members=max_agents)
        self._agents: dict[str, Agent] = {}
        self._timeout = timeout
        self._providers_config = providers_config

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

    async def discuss(self, topic: str) -> list[AgentResponse]:
        """
        Start a discussion on a topic.

        All agents respond to the topic concurrently.

        Args:
            topic: Discussion topic

        Returns:
            List of agent responses
        """
        # Add user message to memory
        self._chatroom.memory.add_message(role="user", content=topic)

        # Get messages for context
        messages = self._chatroom.memory.get_messages_for_agent()

        # Create tasks for all agents
        tasks = []
        for agent in self._agents.values():
            if agent.is_active:
                tasks.append(self._call_agent(agent, messages))

        # Wait for all responses
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        results = []
        agent_list = list(self._agents.values())
        for i, response in enumerate(responses):
            if i >= len(agent_list):
                continue
            agent = agent_list[i]
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
