import discord
from discord.ext import commands

from services.player_info_service import IPlayerInfoService


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
        if not player_id:
            await ctx.send("❌ Please provide a player ID. Usage: `!stats {player_id}`")
            return

        # Send a loading message
        loading_msg = await ctx.send(f"🔍 Fetching stats for player `{player_id}`...")

        try:
            # Fetch player info
            player_data = await self._player_info_service.get_player_info(player_id)

            if player_data is None:
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

        except Exception as e:
            await loading_msg.edit(content=f"❌ An error occurred while fetching player stats: {str(e)}")
            print(f"Error in player stats handler: {e}")
