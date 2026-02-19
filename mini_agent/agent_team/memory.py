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

    def get_messages_for_agent(self, current_agent_name: Optional[str] = None) -> list[dict]:
        """
        Get messages formatted for LLM context with proper role mapping.

        Role mapping:
        - "user" messages -> role="user" (unchanged)
        - "agent" messages from current_agent_name -> role="assistant"
        - "agent" messages from other agents -> role="user" with "[AgentName]: " prefix

        Args:
            current_agent_name: Name of the agent receiving these messages.
                               Used to identify its own messages as "assistant" role.

        Returns:
            List of message dicts with valid LLM API roles (user/assistant).
        """
        result = []
        for msg in self.messages:
            if msg.role == "user":
                result.append({"role": "user", "content": msg.content})
            elif msg.role == "agent":
                if current_agent_name and msg.agent_name == current_agent_name:
                    result.append({"role": "assistant", "content": msg.content})
                else:
                    speaker = msg.agent_name or "Unknown"
                    result.append({
                        "role": "user",
                        "content": f"[{speaker}]: {msg.content}"
                    })
            else:
                result.append({"role": msg.role, "content": msg.content})
        return result

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def count(self) -> int:
        """Get message count."""
        return len(self.messages)

    class Config:
        """Pydantic configuration."""
        extra = "allow"
