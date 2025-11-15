import discord
import os
from dotenv import load_dotenv
from gemini import translate_to_english, translate_to_language

from discord.ext import commands

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    # Stop further processing if the message was a command or sent in a DM
    if message.content.startswith(bot.command_prefix) or not message.guild:
        return

    role_name = "Translator"

    role = discord.utils.get(message.guild.roles, name=role_name)

    # If the user has the role, translate their message
    if role and role in message.author.roles:
        # Avoid translating empty messages or potential bot commands
        if not message.content or message.content.startswith(("!", "$", "/", "?")):
            return

        try:
            # Show that the bot is working
            translation_data = translate_to_english(message.content)

            # Proceed only if we got data and the language is not English
            if translation_data and translation_data.get("language") != "English":
                translated_text = translation_data.get("text")
                # Reply to the original message with the translation
                await message.reply(f"> {translated_text}")
        except Exception as e:
            print(f"An error occurred during translation or sending: {e}")
            await message.channel.send("Sorry, I couldn't translate that.")

@bot.command(name="translate")
async def translate_command(ctx, *, target_language: str):
    """Translates a replied-to message into a specified language."""
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
            translated_text = translate_to_language(text_to_translate, target_language)

        if translated_text:
            await ctx.reply(f"Translated to {target_language}:\n> {translated_text.get("text")}")
        else:
            await ctx.reply(f"Sorry, I couldn't translate that to {target_language}.")
    except Exception as e:
        print(f"Error in !translate command: {e}")
        await ctx.reply("An error occurred while processing your request.")


@bot.command(name="en")
async def en_command(ctx):
    """Translates a replied-to message into English."""
    if not ctx.message.reference:
        await ctx.reply("You need to reply to a message to use this command.")
        return

    try:
        original_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        text_to_translate = original_message.content

        if not text_to_translate:
            await ctx.reply("The replied-to message is empty.")
            return

        translation_data = translate_to_english(text_to_translate)

        if translation_data and translation_data.get("language") != "English":
            translated_text = translation_data.get("text")
            await ctx.reply(f"Translated from {translation_data.get('language')}:\n> {translated_text}")
        elif translation_data:
            await ctx.reply("The message is already in English.")
        else:
            await ctx.reply("Sorry, I couldn't translate that.")
    except Exception as e:
        print(f"Error in !en command: {e}")
        await ctx.reply("An error occurred while translating.")

@en_command.error
async def en_command_error(ctx, error):
    """Handles errors for the !en command, specifically for missing roles."""
    if isinstance(error, commands.MissingRole):
        await ctx.reply("You do not have the required 'Translator' role to use this command.")
    else:
        # Handle other potential errors
        print(f"An unhandled error occurred in !en command: {error}")
        await ctx.reply("An unexpected error occurred.")

bot.run(os.getenv("DISCORD_TOKEN"))
