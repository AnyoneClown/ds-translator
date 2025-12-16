import discord
from discord.ext import commands
import logging

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

        @self._bot.command(name="stats")
        async def get_player_stats(ctx, player_id: str = None):
            """Fetch and display player statistics. Usage: !stats {player_id}"""
            await self._handle_player_stats(ctx, player_id)

    async def _handle_player_stats(self, ctx: commands.Context, player_id: str = None):
        """
        Handle the stats command.

        Args:
            ctx: Discord command context
            player_id: The player ID to look up
        """
        user_info = f"{ctx.author.name}#{ctx.author.discriminator} (ID: {ctx.author.id})"
        guild_info = f"{ctx.guild.name} (ID: {ctx.guild.id})" if ctx.guild else "DM"
        
        if not player_id:
            logger.info(f"Stats command called without player_id by {user_info} in {guild_info}")
            await ctx.send("❌ Please provide a player ID. Usage: `!stats {player_id}`")
            return

        logger.info(f"Stats command for player {player_id} requested by {user_info} in {guild_info}")
        
        # Send a loading message
        loading_msg = await ctx.send(f"🔍 Fetching stats for player `{player_id}`...")

        try:
            # Fetch player info
            player_data = await self._player_info_service.get_player_info(player_id)

            if player_data is None:
                logger.warning(f"Player {player_id} not found for request by {user_info}")
                await loading_msg.edit(content=f"❌ Could not find player with ID: `{player_id}`")
                return

            # Format the response
            formatted_stats = self._player_info_service.format_player_stats(player_data)
            
            # Get player name for title
            player_name = player_data.get("name", f"Player {player_id}")

            # Create an embed for better presentation
            embed = discord.Embed(
                title=f"📊 {player_name}", description=formatted_stats, color=discord.Color.blue()
            )
            
            # Add profile photo if available
            if "profilePhoto" in player_data and player_data["profilePhoto"]:
                embed.set_thumbnail(url=player_data["profilePhoto"])
            
            embed.set_footer(text="Data from kingshot.net API")

            await loading_msg.edit(content=None, embed=embed)
            logger.info(f"Successfully displayed stats for {player_name} (ID: {player_id}) to {user_info}")

        except Exception as e:
            logger.error(f"Error handling stats command for player {player_id} by {user_info}: {e}", exc_info=True)
            await loading_msg.edit(content=f"❌ An error occurred while fetching player stats: {str(e)}")
