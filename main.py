"""
Discord Translation Bot - Main Entry Point
Follows SOLID principles for maintainability and extensibility.
"""

import discord
from discord.ext import commands
from google import genai
import logging
import os

from config import BotConfig
from config.logging_config import setup_logging
from handlers import EventHandler, PlayerInfoHandler, TranslationHandler
from services import EventSchedulerService, PlayerInfoService, TranslationService

logger = logging.getLogger(__name__)


class TranslatorBot:
    """Main bot class - Dependency Injection and Single Responsibility."""

    def __init__(self, config: BotConfig):
        """
        Initialize the bot with configuration and services.

        Args:
            config: Bot configuration object
        """
        self.config = config
        logger.info("Initializing TranslatorBot")

        # Setup Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        self.bot = commands.Bot(command_prefix=config.command_prefix, intents=intents)
        logger.info(f"Discord bot created with prefix: {config.command_prefix}")

        # Initialize services
        logger.info("Initializing services...")
        gemini_client = genai.Client()
        self.translation_service = TranslationService(gemini_client)
        self.event_scheduler_service = EventSchedulerService()
        self.player_info_service = PlayerInfoService()
        logger.info("All services initialized")

        # Initialize handlers
        logger.info("Initializing handlers...")
        self.translation_handler = TranslationHandler(self.translation_service, self.bot)
        self.event_handler = EventHandler(self.event_scheduler_service, self.bot)
        self.player_info_handler = PlayerInfoHandler(self.player_info_service, self.bot)
        logger.info("All handlers initialized")

        # Setup bot
        self._setup_events()
        self._setup_handlers()
        logger.info("Bot setup complete")

    def _setup_events(self):
        """Register bot events."""

        @self.bot.event
        async def on_ready():
            logger.info("=" * 80)
            logger.info(f"Bot logged in as {self.bot.user}")
            logger.info(f"Bot ID: {self.bot.user.id}")
            logger.info(f"Command prefix: {self.config.command_prefix}")
            logger.info(f"Connected to {len(self.bot.guilds)} guild(s)")
            for guild in self.bot.guilds:
                logger.info(f"  - {guild.name} (ID: {guild.id}) - {guild.member_count} members")
            logger.info("=" * 80)
            self.event_handler.start_scheduler_task()
            logger.info("Event scheduler task started")
        
        @self.bot.event
        async def on_command_error(ctx, error):
            """Handle command errors."""
            if isinstance(error, commands.CommandNotFound):
                logger.warning(f"Unknown command attempted by {ctx.author}: {ctx.message.content}")
            elif isinstance(error, commands.MissingRequiredArgument):
                logger.warning(f"Missing argument for command by {ctx.author}: {ctx.command}")
                await ctx.send(f"❌ Missing required argument: {error.param.name}")
            elif isinstance(error, commands.BadArgument):
                logger.warning(f"Bad argument for command by {ctx.author}: {ctx.command} - {error}")
                await ctx.send(f"❌ Invalid argument provided")
            else:
                logger.error(f"Command error in {ctx.command} by {ctx.author}: {error}", exc_info=error)
                await ctx.send(f"❌ An error occurred while processing the command")
        
        @self.bot.event
        async def on_guild_join(guild):
            """Log when bot joins a guild."""
            logger.info(f"Bot joined new guild: {guild.name} (ID: {guild.id}) - {guild.member_count} members")
        
        @self.bot.event
        async def on_guild_remove(guild):
            """Log when bot leaves a guild."""
            logger.info(f"Bot removed from guild: {guild.name} (ID: {guild.id})")

    def _setup_handlers(self):
        """Register all command and event handlers."""
        logger.info("Registering command handlers...")
        self.translation_handler.register_commands()
        self.translation_handler.register_events()
        self.event_handler.register_commands()
        self.player_info_handler.register_commands()
        logger.info("All command handlers registered")

    def run(self):
        """Start the bot."""
        logger.info("Starting Discord bot...")
        try:
            self.bot.run(self.config.discord_token)
        except KeyboardInterrupt:
            logger.info("Bot shutdown requested by user")
        except Exception as e:
            logger.critical(f"Fatal error running bot: {e}", exc_info=True)
            raise


def main():
    """Main entry point for the application."""
    # Setup logging first
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)
    
    logger.info("Starting Discord Translator Bot application")
    
    try:
        config = BotConfig.from_env()
        bot = TranslatorBot(config)
        bot.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
