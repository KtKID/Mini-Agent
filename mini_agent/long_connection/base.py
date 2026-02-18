"""
Long Connection Platform Abstract Base Class

Defines the interface for all long connection platform implementations.
"""

from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Optional
from dataclasses import dataclass
from enum import Enum


class ConnectionState(Enum):
    """Connection states for a platform."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class PlatformMessage:
    """Message received from a platform."""
    platform_id: str
    user_id: str
    content: str
    message_id: str
    timestamp: str


class LongConnectionPlatform(ABC):
    """
    Abstract base class for long connection platform implementations.

    All platforms (Feishu, Slack, Discord, etc.) must implement this interface.
    """

    def __init__(self, platform_id: str):
        """
        Initialize the platform.

        Args:
            platform_id: Unique identifier for this platform (e.g., "feishu", "slack")
        """
        self.platform_id = platform_id
        self._state = ConnectionState.DISCONNECTED
        self._message_callback: Optional[Callable[[PlatformMessage], Awaitable[None]]] = None
        self._error_callback: Optional[Callable[[Exception], Awaitable[None]]] = None
        self._disconnect_callback: Optional[Callable[[], Awaitable[None]]] = None

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if the platform is currently connected."""
        return self._state == ConnectionState.CONNECTED

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish the long connection to the platform.

        This should be a blocking operation that establishes the connection
        and starts listening for events.

        Raises:
            ConnectionError: If the connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Gracefully close the connection to the platform.

        This should clean up all resources and stop any running tasks.
        """
        pass

    def on_message(self, callback: Callable[[PlatformMessage], Awaitable[None]]) -> None:
        """
        Register a callback for incoming messages.

        Args:
            callback: Async function that handles PlatformMessage
        """
        self._message_callback = callback

    def on_error(self, callback: Callable[[Exception], Awaitable[None]]) -> None:
        """
        Register a callback for connection errors.

        Args:
            callback: Async function that handles Exception
        """
        self._error_callback = callback

    def on_disconnect(self, callback: Callable[[], Awaitable[None]]) -> None:
        """
        Register a callback for disconnection events.

        Args:
            callback: Async function called when disconnected
        """
        self._disconnect_callback = callback

    async def _handle_message(self, message: PlatformMessage) -> None:
        """Internal method to dispatch message to callback."""
        if self._message_callback:
            try:
                await self._message_callback(message)
            except Exception as e:
                if self._error_callback:
                    await self._error_callback(e)

    async def _handle_error(self, error: Exception) -> None:
        """Internal method to dispatch error to callback."""
        if self._error_callback:
            await self._error_callback(error)

    async def _handle_disconnect(self) -> None:
        """Internal method to dispatch disconnect event."""
        if self._disconnect_callback:
            await self._disconnect_callback()

    def _set_state(self, state: ConnectionState) -> None:
        """Internal method to update connection state."""
        self._state = state
