import logging

import discord
from discord import app_commands
from discord.ext import commands

from db import get_db
from services.database_service import DatabaseService
from services.player_info_service import IPlayerInfoService

logger = logging.getLogger(__name__)


class PlayerInfoHandler:
    """Handles player info Discord commands."""

    def __init__(self, player_info_service: IPlayerInfoService, bot: commands.Bot):
        """
        Initialize player info handler.

        Args:
            player_info_service: Service for fetching player information
            bot: Discord bot instance
        """
        self._player_info_service = player_info_service
        self._bot = bot
        logger.info("PlayerInfoHandler initialized")

    def register_commands(self):
        """Register all player info commands with the bot."""

        @self._bot.tree.command(name="stats", description="Fetch and display player statistics")
        @app_commands.describe(player_id="The player ID to look up")
        async def get_player_stats(interaction: discord.Interaction, player_id: str):
            """Fetch and display player statistics."""
            await self._handle_player_stats_slash(interaction, player_id)

    async def _handle_player_stats_slash(self, interaction: discord.Interaction, player_id: str):
        """
        Handle the stats command (slash command).

        Args:
            interaction: Discord interaction
            player_id: The player ID to look up
        """
        await interaction.response.defer(thinking=True)

        user_info = f"{interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})"
        guild_info = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"

        logger.info(f"Stats command for player {player_id} requested by {user_info} in {guild_info}")

        try:
            # Fetch player info
            player_data = await self._player_info_service.get_player_info(player_id)

            if player_data is None:
                logger.warning(f"Player {player_id} not found for request by {user_info}")
                await interaction.followup.send(f"❌ Could not find player with ID: `{player_id}`")

                # Track failed lookup in database
                try:
                    db = get_db()
                    async with db.session() as session:
                        await DatabaseService.get_or_create_user(
                            session,
                            interaction.user.id,
                            interaction.user.name,
                            interaction.user.discriminator,
                            interaction.user.display_name,
                        )
                        await DatabaseService.log_player_lookup(
                            session,
                            user_id=interaction.user.id,
                            player_id=player_id,
                            success=False,
                            guild_id=interaction.guild_id,
                            channel_id=interaction.channel_id,
                        )
                except Exception as db_error:
                    logger.error(f"Database tracking error: {db_error}", exc_info=True)

                return

            # Format the response
            formatted_stats = self._player_info_service.format_player_stats(player_data)

            # Get player name for title
            player_name = player_data.get("name", f"Player {player_id}")

            # Create an embed for better presentation
            embed = discord.Embed(
                title=f"📊 {player_name}",
                description=formatted_stats,
                color=discord.Color.blue(),
            )

            # Add profile photo if available
            if "profilePhoto" in player_data and player_data["profilePhoto"]:
                embed.set_thumbnail(url=player_data["profilePhoto"])

            embed.set_footer(text="Data from kingshot.net API")

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully displayed stats for {player_name} (ID: {player_id}) to {user_info}")

            # Track in database
            try:
                db = get_db()
                async with db.session() as session:
                    # Get or create user
                    await DatabaseService.get_or_create_user(
                        session,
                        interaction.user.id,
                        interaction.user.name,
                        interaction.user.discriminator,
                        interaction.user.display_name,
                    )
                    # Log the successful player lookup with kingdom and castle level
                    await DatabaseService.log_player_lookup(
                        session,
                        user_id=interaction.user.id,
                        player_id=player_id,
                        player_name=player_name,
                        kingdom=(str(player_data.get("kingdom")) if player_data.get("kingdom") else None),
                        castle_level=player_data.get("levelRenderedDetailed"),
                        success=True,
                        guild_id=interaction.guild_id,
                        channel_id=interaction.channel_id,
                    )
                    logger.debug(f"Tracked player stats request by user {interaction.user.id}")
            except Exception as db_error:
                logger.error(f"Database tracking error: {db_error}", exc_info=True)

        except Exception as e:
            logger.error(
                f"Error handling stats command for player {player_id} by {user_info}: {e}",
                exc_info=True,
            )
            await interaction.followup.send(f"❌ An error occurred while fetching player stats: {str(e)}")
