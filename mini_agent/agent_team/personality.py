"""
Personality Configuration

Defines the personality traits for agents.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Personality(BaseModel):
    """
    Agent personality configuration.

    Defines the system prompt and response style for an agent.
    """

    name: str = Field(
        description="Personality name, e.g., 'Professional', 'Friendly'"
    )

    system_prompt: str = Field(
        description="System prompt that defines agent behavior"
    )

    response_style: Optional[str] = Field(
        default=None,
        description="Response style description"
    )

    class Config:
        """Pydantic configuration."""
        extra = "allow"
