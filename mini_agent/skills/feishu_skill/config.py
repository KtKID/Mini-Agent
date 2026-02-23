"""
Feishu Skill Configuration

Configuration model for the Feishu Skill with support for enable/disable.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FeishuConfig(BaseModel):
    """
    Configuration for Feishu Skill integration.

    This config is loaded from the main config.yaml under the 'feishu' key.
    """

    enabled: bool = Field(
        default=False,
        description="Enable or disable the Feishu Skill"
    )

    app_id: Optional[str] = Field(
        default=None,
        description="Feishu application ID (must start with 'cli_')"
    )

    app_secret: Optional[str] = Field(
        default=None,
        description="Feishu application secret"
    )

    encrypt_key: Optional[str] = Field(
        default=None,
        description="Message encryption key (optional)"
    )

    verification_token: Optional[str] = Field(
        default=None,
        description="Verification token for callback URL validation (optional for WebSocket mode)"
    )

    # Session configuration
    max_sessions: int = Field(
        default=100,
        description="Maximum concurrent user sessions"
    )

    session_timeout: int = Field(
        default=3600,
        description="Session timeout in seconds"
    )

    # Reconnection configuration
    reconnect_initial_delay: float = Field(
        default=1.0,
        description="Initial reconnect delay in seconds"
    )

    reconnect_max_delay: float = Field(
        default=30.0,
        description="Maximum reconnect delay in seconds"
    )

    reconnect_max_retries: int = Field(
        default=10,
        description="Maximum number of consecutive retry attempts"
    )

    @field_validator("app_id")
    @classmethod
    def validate_app_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate app_id format if provided."""
        if v is not None and not v.startswith("cli_"):
            raise ValueError("app_id must start with 'cli_'")
        return v

    @field_validator("app_secret")
    @classmethod
    def validate_app_secret(cls, v: Optional[str]) -> Optional[str]:
        """Validate app_secret is not empty if provided."""
        if v is not None and len(v) == 0:
            raise ValueError("app_secret cannot be empty")
        return v

    @field_validator("max_sessions")
    @classmethod
    def validate_max_sessions(cls, v: int) -> int:
        """Validate max_sessions is positive."""
        if v <= 0:
            raise ValueError("max_sessions must be positive")
        return v

    @field_validator("session_timeout")
    @classmethod
    def validate_session_timeout(cls, v: int) -> int:
        """Validate session_timeout is at least 60 seconds."""
        if v < 60:
            raise ValueError("session_timeout must be at least 60 seconds")
        return v

    def is_valid(self) -> bool:
        """
        Check if the configuration is valid for enabling the Skill.

        Returns:
            True if enabled and has valid credentials
        """
        if not self.enabled:
            return True

        return (
            self.app_id is not None
            and self.app_secret is not None
            and self.app_id.startswith("cli_")
            and len(self.app_secret) > 0
        )

    class Config:
        """Pydantic configuration."""
        extra = "allow"
