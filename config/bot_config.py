"""Configuration module for bot settings."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class BotConfig:
    """Bot configuration settings."""

    discord_token: str
    database_url: str
    command_prefix: str = "!"
    translator_role_name: str = "Translator"
    banned_players: set = None
    auto_redeem_channels: set = None

    def __post_init__(self):
        """Initialize mutable default values."""
        if self.banned_players is None:
            self.banned_players = set()
        if self.auto_redeem_channels is None:
            self.auto_redeem_channels = set()

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables."""
        load_dotenv()

        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_TOKEN not found in environment variables")

        database_url = os.getenv("COCKROACHDB_URL")
        if not database_url:
            raise ValueError("COCKROACHDB_URL not found in environment variables")

        # Parse banned players from environment variable (comma-separated user IDs)
        banned_players_str = os.getenv("BANNED_PLAYERS", "")
        banned_players = set()
        if banned_players_str.strip():
            try:
                banned_players = set(
                    int(user_id.strip()) for user_id in banned_players_str.split(",") if user_id.strip()
                )
            except ValueError:
                raise ValueError("BANNED_PLAYERS must contain comma-separated user IDs (integers)")

        # Parse auto redeem announcement channels from environment variable (comma-separated channel IDs)
        auto_redeem_channels_str = os.getenv("AUTO_REDEEM_CHANNELS", "")
        auto_redeem_channels = set()
        if auto_redeem_channels_str.strip():
            try:
                auto_redeem_channels = set(
                    int(channel_id.strip()) for channel_id in auto_redeem_channels_str.split(",") if channel_id.strip()
                )
            except ValueError:
                raise ValueError("AUTO_REDEEM_CHANNELS must contain comma-separated channel IDs (integers)")

        return cls(
            discord_token=discord_token,
            database_url=database_url,
            command_prefix=os.getenv("COMMAND_PREFIX", "!"),
            translator_role_name=os.getenv("TRANSLATOR_ROLE", "Translator"),
            banned_players=banned_players,
            auto_redeem_channels=auto_redeem_channels,
        )
