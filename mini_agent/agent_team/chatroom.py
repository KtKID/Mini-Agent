"""
Chatroom - Multi-agent discussion space

Manages agents and shared memory for collaborative discussions.
"""

import uuid
import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from mini_agent.agent_team.agent import Agent, AgentConfig
from mini_agent.agent_team.memory import Memory


class Chatroom(BaseModel):
    """
    Chatroom for multi-agent discussions.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique chatroom identifier"
    )

    name: str = Field(
        description="Chatroom name"
    )

    created_at: float = Field(
        default_factory=lambda: __import__("time").time(),
        description="Creation timestamp"
    )

    max_members: int = Field(
        default=10,
        description="Maximum number of agents"
    )

    memory: Memory = Field(
        default_factory=Memory,
        description="Shared memory for all agents"
    )

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class ChatroomManager:
    """
    Manager for Chatroom instances.
    """

    def __init__(self, max_chatrooms: int = 10):
        """
        Initialize chatroom manager.

        Args:
            max_chatrooms: Maximum number of chatrooms
        """
        self.max_chatrooms = max_chatrooms
        self._chatrooms: dict[str, Chatroom] = {}

    def create_chatroom(self, name: str, max_members: int = 10) -> Chatroom:
        """
        Create a new chatroom.

        Args:
            name: Chatroom name
            max_members: Maximum members

        Returns:
            Created chatroom
        """
        if len(self._chatrooms) >= self.max_chatrooms:
            raise ValueError(f"Maximum number of chatrooms ({self.max_chatrooms}) reached")

        chatroom = Chatroom(name=name, max_members=max_members)
        self._chatrooms[chatroom.id] = chatroom
        return chatroom

    def get_chatroom(self, chatroom_id: str) -> Optional[Chatroom]:
        """Get chatroom by ID."""
        return self._chatrooms.get(chatroom_id)

    def list_chatrooms(self) -> list[Chatroom]:
        """List all chatrooms."""
        return list(self._chatrooms.values())

    def delete_chatroom(self, chatroom_id: str) -> bool:
        """Delete a chatroom."""
        if chatroom_id in self._chatrooms:
            del self._chatrooms[chatroom_id]
            return True
        return False
