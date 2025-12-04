"""
Discord Translation Bot - Main Entry Point
Follows SOLID principles for maintainability and extensibility.
"""

import discord
from discord.ext import commands
from google import genai

from config import BotConfig
from services import TranslationService, EventSchedulerService
from handlers import TranslationHandler, EventHandler


class TranslatorBot:
    """Main bot class - Dependency Injection and Single Responsibility."""

    def __init__(self, config: BotConfig):
        """
        Initialize the bot with configuration and services.
        
        Args:
            config: Bot configuration object
        """
        self.config = config
        
        # Setup Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        self.bot = commands.Bot(command_prefix=config.command_prefix, intents=intents)
        
        # Initialize services
        gemini_client = genai.Client()
        self.translation_service = TranslationService(gemini_client)
        self.event_scheduler_service = EventSchedulerService()
        
        # Initialize handlers
        self.translation_handler = TranslationHandler(self.translation_service, self.bot)
        self.event_handler = EventHandler(self.event_scheduler_service, self.bot)
        
        # Setup bot
        self._setup_events()
        self._setup_handlers()

    def _setup_events(self):
        """Register bot events."""
        
        @self.bot.event
        async def on_ready():
            print(f"Bot logged in as {self.bot.user}")
            print(f"Command prefix: {self.config.command_prefix}")
            print(f"Guilds: {len(self.bot.guilds)}")
            self.event_handler.start_scheduler_task()

    def _setup_handlers(self):
        """Register all command and event handlers."""
        self.translation_handler.register_commands()
        self.translation_handler.register_events()
        self.event_handler.register_commands()

    def run(self):
        """Start the bot."""
        print("Starting Discord Translator Bot...")
        self.bot.run(self.config.discord_token)


def main():
    """Main entry point for the application."""
    try:
        config = BotConfig.from_env()
        bot = TranslatorBot(config)
        bot.run()
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Failed to start bot: {e}")


if __name__ == "__main__":
    main()
