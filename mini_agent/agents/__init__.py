"""
Agent configuration loader.

Loads agent definitions from agents.yaml and personality templates
from the personalities/ directory.
"""

import os
from pathlib import Path
from typing import Optional, Union

import yaml
from pydantic import BaseModel, Field

from mini_agent.agent_team.personality import Personality


class InlinePersonalityConfig(BaseModel):
    """Inline personality definition in agents.yaml."""

    name: str
    system_prompt: str
    response_style: Optional[str] = None


class AgentDefinition(BaseModel):
    """Single agent definition from agents.yaml."""

    name: str
    provider_id: str
    model_name: str
    personality: Union[str, InlinePersonalityConfig]


class AgentsFileConfig(BaseModel):
    """Root schema for agents.yaml."""

    agents: list[AgentDefinition] = Field(default_factory=list)


class AgentConfigLoader:
    """Loads agent configurations from agents.yaml and personality templates."""

    def __init__(self, agents_dir: Optional[str] = None):
        if agents_dir is None:
            agents_dir = str(Path(__file__).parent)
        self._agents_dir = agents_dir
        self._personalities_dir = os.path.join(agents_dir, "personalities")
        self._agents_yaml = os.path.join(agents_dir, "agents.yaml")
        self._personality_templates: dict[str, Personality] = {}

    def load_personality_templates(self) -> dict[str, Personality]:
        """Load all personality templates from personalities/ directory.

        Returns:
            Dict keyed by template name (filename without extension).
        """
        templates = {}
        if not os.path.isdir(self._personalities_dir):
            return templates
        for fname in sorted(os.listdir(self._personalities_dir)):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                template_name = fname.rsplit(".", 1)[0]
                filepath = os.path.join(self._personalities_dir, fname)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                templates[template_name] = Personality(
                    name=data.get("name", template_name),
                    system_prompt=data["system_prompt"],
                    response_style=data.get("response_style"),
                )
        self._personality_templates = templates
        return templates

    def load_agents(self) -> list[AgentDefinition]:
        """Load agent definitions from agents.yaml."""
        if not os.path.isfile(self._agents_yaml):
            return []
        with open(self._agents_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        config = AgentsFileConfig(**data)
        return config.agents

    def resolve_personality(self, agent_def: AgentDefinition) -> Personality:
        """Resolve personality from template reference or inline definition.

        Args:
            agent_def: Agent definition with personality as str (template name)
                       or InlinePersonalityConfig (inline definition).

        Returns:
            Resolved Personality object.
        """
        if isinstance(agent_def.personality, str):
            template_name = agent_def.personality
            if template_name not in self._personality_templates:
                available = list(self._personality_templates.keys())
                raise ValueError(
                    f"Personality template '{template_name}' not found. "
                    f"Available: {available}"
                )
            return self._personality_templates[template_name]
        else:
            return Personality(
                name=agent_def.personality.name,
                system_prompt=agent_def.personality.system_prompt,
                response_style=agent_def.personality.response_style,
            )
