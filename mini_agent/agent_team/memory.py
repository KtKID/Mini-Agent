"""
Memory - Shared conversation history for chatroom

Stores messages that all agents can access.
"""

import time
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Message(BaseModel):
    """
    Single message in the conversation.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message identifier")
    role: str = Field(description="Role: user or agent")
    agent_id: Optional[str] = Field(default=None, description="Agent ID (for agent role)")
    agent_name: Optional[str] = Field(default=None, description="Agent name (for agent role)")
    content: str = Field(description="Message content")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class Memory(BaseModel):
    """
    Shared memory for chatroom.

    All agents in the chatroom share this memory.
    """

    messages: list[Message] = Field(
        default_factory=list,
        description="List of messages in the conversation"
    )

    max_tokens: int = Field(
        default=100000,
        description="Maximum number of tokens to store"
    )

    created_at: float = Field(
        default_factory=time.time,
        description="Creation timestamp"
    )

    def add_message(self, role: str, content: str, agent_id: Optional[str] = None, agent_name: Optional[str] = None) -> Message:
        """
        Add a message to memory.

        Args:
            role: Message role (user/agent)
            content: Message content
            agent_id: Agent ID (if role is agent)
            agent_name: Agent name (if role is agent)

        Returns:
            Created message
        """
        import uuid
        message = Message(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            agent_id=agent_id,
            agent_name=agent_name
        )
        self.messages.append(message)
        return message

    def get_messages(self) -> list[Message]:
        """Get all messages."""
        return self.messages

    def get_messages_for_agent(self) -> list[dict]:
        """
        Get messages formatted for LLM context.

        Returns:
            List of message dicts with role and content
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def count(self) -> int:
        """Get message count."""
        return len(self.messages)

    class Config:
        """Pydantic configuration."""
        extra = "allow"
