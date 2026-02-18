"""
Long Connection Registry

Manages registration of long connection platform implementations.
"""

import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mini_agent.long_connection.base import LongConnectionPlatform

logger = logging.getLogger(__name__)


class LongConnectionRegistry:
    """
    Singleton registry for managing long connection platform implementations.

    This registry allows platforms to be registered and retrieved by their ID.
    Multiple platforms can be registered simultaneously (e.g., Feishu + Slack).
    """

    _instance: Optional["LongConnectionRegistry"] = None
    _platforms: Dict[str, "LongConnectionPlatform"] = {}

    def __new__(cls) -> "LongConnectionRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._platforms = {}
            logger.debug("LongConnectionRegistry initialized")
        return cls._instance

    @property
    def platforms(self) -> Dict[str, "LongConnectionPlatform"]:
        """Get all registered platforms."""
        return self._platforms

    def register(self, platform: "LongConnectionPlatform") -> None:
        """
        Register a platform implementation.

        Args:
            platform: Platform instance implementing LongConnectionPlatform

        Raises:
            ValueError: If a platform with the same ID is already registered
        """
        platform_id = platform.platform_id

        if platform_id in self._platforms:
            logger.warning(
                f"Platform '{platform_id}' is already registered. "
                f"Replacing existing instance."
            )

        self._platforms[platform_id] = platform
        logger.info(f"Registered platform: {platform_id}")

    def unregister(self, platform_id: str) -> None:
        """
        Unregister a platform by its ID.

        Args:
            platform_id: ID of the platform to unregister

        Raises:
            KeyError: If the platform ID is not found
        """
        if platform_id not in self._platforms:
            raise KeyError(f"Platform '{platform_id}' is not registered")

        del self._platforms[platform_id]
        logger.info(f"Unregistered platform: {platform_id}")

    def get(self, platform_id: str) -> "LongConnectionPlatform":
        """
        Get a registered platform by its ID.

        Args:
            platform_id: ID of the platform to retrieve

        Returns:
            The platform instance

        Raises:
            KeyError: If the platform ID is not found
        """
        if platform_id not in self._platforms:
            raise KeyError(f"Platform '{platform_id}' is not registered")

        return self._platforms[platform_id]

    def get_all(self) -> List["LongConnectionPlatform"]:
        """
        Get all registered platforms.

        Returns:
            List of all registered platform instances
        """
        return list(self._platforms.values())

    def get_ids(self) -> List[str]:
        """
        Get IDs of all registered platforms.

        Returns:
            List of platform IDs
        """
        return list(self._platforms.keys())

    def is_registered(self, platform_id: str) -> bool:
        """
        Check if a platform is registered.

        Args:
            platform_id: ID of the platform to check

        Returns:
            True if the platform is registered
        """
        return platform_id in self._platforms

    def clear(self) -> None:
        """Clear all registered platforms."""
        self._platforms.clear()
        logger.info("Cleared all registered platforms")

    async def connect_all(self) -> None:
        """Connect all registered platforms."""
        for platform in self._platforms.values():
            try:
                await platform.connect()
            except Exception as e:
                logger.error(
                    f"Failed to connect platform '{platform.platform_id}': {e}"
                )

    async def disconnect_all(self) -> None:
        """Disconnect all registered platforms."""
        for platform in self._platforms.values():
            try:
                await platform.disconnect()
            except Exception as e:
                logger.error(
                    f"Failed to disconnect platform '{platform.platform_id}': {e}"
                )

    def get_connected(self) -> List["LongConnectionPlatform"]:
        """
        Get all platforms that are currently connected.

        Returns:
            List of connected platform instances
        """
        return [p for p in self._platforms.values() if p.is_connected]
