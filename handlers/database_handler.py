"""Handler for database-related commands."""

import logging

from discord.ext import commands

logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Handles database-related commands."""

    def __init__(self, bot: commands.Bot):
        """
        Initialize the database handler.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        logger.info("DatabaseHandler initialized")

    def register_commands(self):
        """Register all database-related commands."""
        logger.info("Registering database commands...")
        logger.info("No database commands registered (UserStats removed)")

    def register_events(self):
        """Register database-related events."""
        logger.info("Database events registered")
