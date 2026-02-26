"""
Feishu Session Manager

Manages user sessions for the Feishu Skill.
"""

import asyncio
import time
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from mini_agent.skills.feishu_skill.logging_config import get_feishu_logger

logger = get_feishu_logger()


@dataclass
class FeishuSession:
    """
    Represents a user session in the Feishu Skill.

    Each session maintains an independent conversation with the user's Agent.
    """
    open_id: str  # 实际存的是 session_id (chat_id or open_id)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0
    agent: Any = None  # Agent 实例，由 SessionManager 通过 factory 创建


class SessionManager:
    """
    Manages multiple user sessions for the Feishu Skill.

    Handles:
    - Session creation and retrieval
    - Session cleanup for expired sessions
    - Concurrent session management
    """

    def __init__(self, config, agent_factory: Optional[Callable] = None):
        """
        Initialize the session manager.

        Args:
            config: FeishuConfig instance
            agent_factory: Optional callable that creates a new Agent instance
        """
        self.config = config
        self._agent_factory = agent_factory

        self._sessions: Dict[str, FeishuSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._sessions)

    @property
    def max_sessions(self) -> int:
        """Get the maximum allowed sessions."""
        return self.config.max_sessions

    def get_or_create(self, session_id: str) -> FeishuSession:
        """
        Get an existing session or create a new one.

        Args:
            session_id: Session identifier (chat_id or open_id)

        Returns:
            FeishuSession instance
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_activity = time.time()
            return session

        if self.session_count >= self.max_sessions:
            raise RuntimeError(
                f"Maximum concurrent sessions ({self.max_sessions}) reached"
            )

        session = FeishuSession(open_id=session_id)
        if self._agent_factory:
            session.agent = self._agent_factory(session_id)
            logger.info(f"SessionManager: Created new session with Agent for {session_id}")
        else:
            logger.info(f"SessionManager: Created new session (no agent) for {session_id}")

        self._sessions[session_id] = session
        return session

    def remove(self, open_id: str) -> bool:
        """
        Remove a session.

        Args:
            open_id: User's Feishu open_id

        Returns:
            True if session was removed, False if not found
        """
        if open_id in self._sessions:
            del self._sessions[open_id]
            logger.info(f"SessionManager: Removed session for {open_id}")
            return True

        return False

    def get_session(self, open_id: str) -> Optional[FeishuSession]:
        """
        Get a session by open_id.

        Args:
            open_id: User's Feishu open_id

        Returns:
            FeishuSession if found, None otherwise
        """
        return self._sessions.get(open_id)

    def has_session(self, open_id: str) -> bool:
        """
        Check if a session exists.

        Args:
            open_id: User's Feishu open_id

        Returns:
            True if session exists
        """
        return open_id in self._sessions

    async def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        timeout = self.config.session_timeout

        expired_ids = [
            open_id
            for open_id, session in self._sessions.items()
            if current_time - session.last_activity > timeout
        ]

        for open_id in expired_ids:
            self.remove(open_id)

        if expired_ids:
            logger.info(
                f"SessionManager: Cleaned up {len(expired_ids)} expired sessions"
            )

        return len(expired_ids)

    async def start_cleanup_task(self, interval: int = 60) -> None:
        """
        Start the background cleanup task.

        Args:
            interval: Cleanup interval in seconds
        """
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(
            self._cleanup_loop(interval)
        )
        logger.info("SessionManager: Started cleanup task")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("SessionManager: Stopped cleanup task")

    async def _cleanup_loop(self, interval: int) -> None:
        """Background loop for session cleanup."""
        while self._running:
            try:
                await asyncio.sleep(interval)
                cleaned = await self.cleanup_expired()
                if cleaned > 0:
                    logger.debug(
                        f"SessionManager: Cleanup complete, "
                        f"{self.session_count} sessions remaining"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SessionManager: Cleanup error: {e}")

    def get_stats(self) -> dict:
        """
        Get session statistics.

        Returns:
            Dictionary with session stats
        """
        total_messages = sum(s.message_count for s in self._sessions.values())
        oldest_session = min(
            (s.created_at for s in self._sessions.values()),
            default=0
        )

        return {
            "active_sessions": self.session_count,
            "max_sessions": self.max_sessions,
            "total_messages": total_messages,
            "oldest_session_age": time.time() - oldest_session if oldest_session else 0,
        }
