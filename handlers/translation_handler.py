from typing import Optional

import discord
from discord.ext import commands

from services.translation_service import ITranslationService


class TranslationHandler:
    """Handles translation-related Discord commands and events."""

    def __init__(self, translation_service: ITranslationService, bot: commands.Bot):
        """
        Initialize translation handler.

        Args:
            translation_service: Service for handling translations
            bot: Discord bot instance
        """
        self._translation_service = translation_service
        self._bot = bot

    def register_commands(self):
        """Register all translation commands with the bot."""

        @self._bot.command(name="t", aliases=["translate"])
        async def translate_command(ctx, *, target_language: str):
            """Translates a replied-to message into a specified language."""
            await self._handle_translate_to_language(ctx, target_language)

        @self._bot.command(name="en")
        async def en_command(ctx):
            """Translates a replied-to message into English."""
            await self._handle_translate_to_english(ctx)

        @en_command.error
        async def en_command_error(ctx, error):
            """Handles errors for the !en command."""
            await self._handle_command_error(ctx, error)

    def register_events(self):
        """Register message events for automatic translation."""

        @self._bot.event
        async def on_message(message):
            if message.author == self._bot.user:
                return

            await self._bot.process_commands(message)

            # Stop if command or DM
            if message.content.startswith(self._bot.command_prefix) or not message.guild:
                return

            await self._handle_auto_translation(message)

    async def _handle_translate_to_language(self, ctx, target_language: str):
        """Handle translation to a specific language command."""
        if not ctx.message.reference:
            await ctx.reply("You need to reply to a message to use this command.")
            return

        try:
            original_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text_to_translate = original_message.content

            if not text_to_translate:
                await ctx.reply("The replied-to message is empty.")
                return

            async with ctx.typing():
                result = self._translation_service.translate_to_language(text_to_translate, target_language)

            if result:
                await ctx.reply(f"Translated to {target_language}:\n> {result.get('text')}")
            else:
                await ctx.reply(f"Sorry, I couldn't translate that to {target_language}.")
        except Exception as e:
            print(f"Error in translate command: {e}")
            await ctx.reply("An error occurred while processing your request.")

    async def _handle_translate_to_english(self, ctx):
        """Handle translation to English command."""
        if not ctx.message.reference:
            await ctx.reply("You need to reply to a message to use this command.")
            return

        try:
            original_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text_to_translate = original_message.content

            if not text_to_translate:
                await ctx.reply("The replied-to message is empty.")
                return

            result = self._translation_service.translate_to_english(text_to_translate)

            if result and result.get("language") != "English":
                translated_text = result.get("text")
                await ctx.reply(f"Translated from {result.get('language')}:\n> {translated_text}")
            elif result:
                await ctx.reply("The message is already in English.")
            else:
                await ctx.reply("Sorry, I couldn't translate that.")
        except Exception as e:
            print(f"Error in !en command: {e}")
            await ctx.reply("An error occurred while translating.")

    async def _handle_auto_translation(self, message: discord.Message):
        """Automatically translate messages from users with Translator role."""
        role_name = "Translator"
        role = discord.utils.get(message.guild.roles, name=role_name)

        if not (role and role in message.author.roles):
            return

        # Skip empty or command-like messages
        if not message.content or message.content.startswith(("!", "$", "/", "?")):
            return

        try:
            result = self._translation_service.translate_to_english(message.content)

            if result and result.get("language") != "English":
                translated_text = result.get("text")
                await message.reply(f"> {translated_text}")
        except Exception as e:
            print(f"Auto-translation error: {e}")
            await message.channel.send("Sorry, I couldn't translate that.")

    async def _handle_command_error(self, ctx, error):
        """Handle errors for translation commands."""
        if isinstance(error, commands.MissingRole):
            await ctx.reply("You do not have the required 'Translator' role to use this command.")
        else:
            print(f"Unhandled error in command: {error}")
            await ctx.reply("An unexpected error occurred.")
