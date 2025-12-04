"""Configuration module for bot settings."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class BotConfig:
    """Bot configuration settings."""
    
    discord_token: str
    command_prefix: str = "!"
    translator_role_name: str = "Translator"
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables."""
        load_dotenv()
        
        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_TOKEN not found in environment variables")
        
        return cls(
            discord_token=discord_token,
            command_prefix=os.getenv("COMMAND_PREFIX", "!"),
            translator_role_name=os.getenv("TRANSLATOR_ROLE", "Translator")
        )
