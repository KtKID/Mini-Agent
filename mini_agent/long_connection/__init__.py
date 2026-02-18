"""
Long Connection Framework

Provides a generic framework for long-running connections to messaging platforms.
This enables Mini Agent to receive messages from various platforms like Feishu,
Slack, Discord, etc. through a standardized interface.

Usage:
    from mini_agent.long_connection import LongConnectionRegistry, LongConnectionPlatform

    # Register a platform
    registry = LongConnectionRegistry()
    registry.register(my_platform)

    # Connect all platforms
    await registry.connect_all()
"""

from mini_agent.long_connection.base import (
    LongConnectionPlatform,
    ConnectionState,
    PlatformMessage,
)
from mini_agent.long_connection.registry import LongConnectionRegistry

__all__ = [
    "LongConnectionPlatform",
    "ConnectionState",
    "PlatformMessage",
    "LongConnectionRegistry",
]
