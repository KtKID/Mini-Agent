"""
Agent - AI Agent configuration and instance

Defines agent configuration and LLM client wrapper.
"""

import uuid
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field

from mini_agent.agent_team.personality import Personality


class ModelProvider(str, Enum):
    """
    Supported AI model providers.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class AgentConfig(BaseModel):
    """
    Agent configuration model.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique agent identifier"
    )

    name: str = Field(
        description="Agent name"
    )

    model_provider: ModelProvider = Field(
        description="Model provider (openai/anthropic/custom)"
    )

    model_name: str = Field(
        description="Model name"
    )

    api_url: Optional[str] = Field(
        default=None,
        description="Custom API URL (required if model_provider is custom)"
    )

    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication"
    )

    personality: Personality = Field(
        description="Personality configuration"
    )

    is_active: bool = Field(
        default=True,
        description="Whether agent is active"
    )

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class Agent:
    """
    Agent instance with LLM client wrapper.

    Wraps the existing LLM client for making API calls.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize agent with configuration.

        Args:
            config: Agent configuration
        """
        self.config = config
        self._llm_client = None

    @property
    def id(self) -> str:
        """Get agent ID."""
        return self.config.id

    @property
    def name(self) -> str:
        """Get agent name."""
        return self.config.name

    @property
    def personality(self) -> Personality:
        """Get agent personality."""
        return self.config.personality

    @property
    def is_active(self) -> bool:
        """Check if agent is active."""
        return self.config.is_active

    def get_system_prompt(self) -> str:
        """Get the system prompt from personality."""
        return self.config.personality.system_prompt

    def get_model_config(self) -> dict:
        """
        Get model configuration for LLM client.

        Returns:
            Dict with provider, model_name, api_url, api_key
        """
        return {
            "provider": self.config.model_provider.value,
            "model_name": self.config.model_name,
            "api_url": self.config.api_url,
            "api_key": self.config.api_key,
        }

    async def generate_response(self, messages: list[dict]) -> str:
        """
        Generate response using the configured LLM.

        Args:
            messages: List of message dicts with role and content

        Returns:
            Generated response text
        """
        # Import existing LLM wrapper and schema
        from mini_agent.llm.llm_wrapper import LLMClient, LLMProvider
        from mini_agent.schema.schema import Message

        # Determine provider
        provider_map = {
            ModelProvider.OPENAI: LLMProvider.OPENAI,
            ModelProvider.ANTHROPIC: LLMProvider.ANTHROPIC,
        }

        provider = provider_map.get(
            self.config.model_provider,
            LLMProvider.OPENAI  # default
        )

        # Create client
        client = LLMClient(
            api_key=self.config.api_key or "",
            provider=provider,
            api_base=self.config.api_url or "",
            model=self.config.model_name,
        )

        # Convert dict messages to Message objects
        message_objects = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages
        ]

        # Add system prompt
        full_messages = [
            Message(role="system", content=self.get_system_prompt())
        ] + message_objects

        # Call LLM
        response = await client.generate(full_messages)
        return response.content

    def deactivate(self) -> None:
        """Deactivate the agent."""
        self.config.is_active = False

    def activate(self) -> None:
        """Activate the agent."""
        self.config.is_active = True

    def update_config(self, **kwargs) -> None:
        """
        Update agent configuration.

        Args:
            **kwargs: Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
