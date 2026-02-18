"""
Provider Configuration

Configuration for different AI model providers.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """Configuration for a single model provider."""

    enabled: bool = Field(default=False, description="Whether this provider is enabled")
    api_url: str = Field(default="", description="API endpoint URL")
    api_key: Optional[str] = Field(default=None, description="API key (or use env var)")
    model_name: Optional[str] = Field(default=None, description="Default model name")

    def get_api_key(self, env_var: str) -> Optional[str]:
        """Get API key from config or environment variable."""
        if self.api_key:
            return self.api_key
        return os.environ.get(env_var)


class ProvidersConfig(BaseModel):
    """Configuration for all model providers."""

    anthropic: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="https://api.anthropic.com"
        ),
        description="Anthropic (Claude) provider"
    )

    openai: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="https://api.openai.com/v1"
        ),
        description="OpenAI (GPT) provider"
    )

    deepseek: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="https://api.deepseek.com/v1"
        ),
        description="DeepSeek provider"
    )

    bigmodel: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="https://open.bigmodel.cn/api/paas/v4"
        ),
        description="BigModel (智谱AI) provider"
    )

    minimax: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="https://api.minimax.chat/v1"
        ),
        description="MiniMax provider"
    )

    ollama: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="http://localhost:11434/v1"
        ),
        description="Ollama (local) provider"
    )

    lmstudio: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="http://127.0.0.1:1234/v1"
        ),
        description="LM Studio (local) provider"
    )

    custom: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(
            enabled=False,
            api_url="http://localhost:8000/v1"
        ),
        description="Custom provider"
    )

    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """Get provider by name."""
        if hasattr(self, name):
            return getattr(self, name)
        return None

    def get_api_key(self, provider_name: str, env_var: str) -> Optional[str]:
        """Get API key for a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.get_api_key(env_var)
        return None


# Environment variable mapping
PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "bigmodel": "BIGMODEL_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "ollama": None,  # Local, no key needed
    "lmstudio": None,  # Local, no key needed
    "custom": "CUSTOM_API_KEY",
}


def get_provider_api_key(provider_name: str, config: ProviderConfig) -> Optional[str]:
    """Get API key from config or environment variable."""
    env_var = PROVIDER_ENV_VARS.get(provider_name)
    if env_var:
        return config.get_api_key(env_var)
    return config.api_key
