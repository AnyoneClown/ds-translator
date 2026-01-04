import logging
from typing import Any, Dict, List

import discord
from discord import app_commands
from discord.ext import commands

from services.kvk_service import IKVKService

logger = logging.getLogger(__name__)


class KVKHandler:
    """Handles KVK (Kingdom vs Kingdom) Discord commands."""

    def __init__(self, kvk_service: IKVKService, bot: commands.Bot):
        """
        Initialize KVK handler.

        Args:
            kvk_service: Service for fetching KVK matches
            bot: Discord bot instance
        """
        self._kvk_service = kvk_service
        self._bot = bot
        logger.info("KVKHandler initialized")

    def register_commands(self):
        """Register all KVK commands with the bot."""

        @self._bot.tree.command(name="kvk", description="Get KVK matches for a kingdom")
        @app_commands.describe(kingdom_number="The kingdom number to fetch matches for (e.g., 1, 2, 3)")
        async def get_kvk_matches(interaction: discord.Interaction, kingdom_number: int):
            """Get KVK matches for a kingdom."""
            await self._handle_get_kvk_matches_slash(interaction, kingdom_number)

    async def _handle_get_kvk_matches_slash(self, interaction: discord.Interaction, kingdom_number: int):
        """
        Handle fetching KVK matches for a kingdom.

        Args:
            interaction: Discord interaction
            kingdom_number: The kingdom number to fetch matches for
        """
        await interaction.response.defer(thinking=True)

        user_info = f"{interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})"
        guild_info = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"

        if kingdom_number <= 0:
            await interaction.followup.send("❌ Kingdom number must be a positive integer.")
            return

        logger.info(f"KVK matches requested for kingdom {kingdom_number} by {user_info} in {guild_info}")

        try:
            # Fetch KVK matches from API
            result = await self._kvk_service.get_kvk_matches(kingdom_number)

            if not result.get("success"):
                await interaction.followup.send(
                    f"❌ Failed to fetch KVK matches for Kingdom {kingdom_number}.\n"
                    f"**Error:** {result.get('message', 'Unknown error')}"
                )
                logger.warning(f"Failed to fetch KVK matches for kingdom {kingdom_number}: {result.get('message')}")
                return

            matches = result.get("data", [])
            pagination = result.get("pagination", {})

            if not matches:
                await interaction.followup.send(f"📭 No KVK matches found for Kingdom {kingdom_number}.")
                return

            # Create main embed
            embed = discord.Embed(
                title=f"⚔️ KVK Matches - Kingdom {kingdom_number}",
                description=f"**Total Matches:** {pagination.get('total', len(matches))}",
                color=discord.Color.red(),
            )

            # Separate matches by result (wins, losses)
            wins = []
            losses = []

            for match in matches:
                kingdom_a = match.get("kingdom_a")
                kingdom_b = match.get("kingdom_b")
                attacker = match.get("attacker")
                defender = match.get("defender")
                castle_winner = match.get("castle_winner")
                prep_winner = match.get("prep_winner")
                castle_captured = match.get("castle_captured", False)
                kvk_title = match.get("kvk_title", "Unknown")
                season_date = match.get("season_date", "N/A")

                # Determine opponent and roles
                opponent = kingdom_b if kingdom_a == kingdom_number else kingdom_a
                is_attacker = attacker == kingdom_number
                is_castle_winner = castle_winner == kingdom_number
                is_prep_winner = prep_winner == kingdom_number

                # Determine castle phase outcome
                if is_castle_winner:
                    castle_result = "🏰 Castle Won"
                    if castle_captured:
                        castle_detail = "(Captured)"
                    else:
                        castle_detail = "(Defended)"
                else:
                    castle_result = "🏰 Castle Lost"
                    if castle_captured:
                        castle_detail = "(Castle Fell)"
                    else:
                        castle_detail = "(Defended)"

                # Attacker/Defender role
                role = "⚔️ Attacker" if is_attacker else "🛡️ Defender"

                # Prep phase result
                prep_result = "🥇 Won Prep" if is_prep_winner else "🥈 Lost Prep"

                match_data = {
                    "title": kvk_title,
                    "opponent": opponent,
                    "date": season_date,
                    "castle_result": castle_result,
                    "castle_detail": castle_detail,
                    "role": role,
                    "prep_result": prep_result,
                    "is_castle_winner": is_castle_winner,
                    "match": match,
                }

                # Separate by castle phase result
                if is_castle_winner:
                    wins.append(match_data)
                else:
                    losses.append(match_data)

            # Add wins field
            if wins:
                wins_text = []
                for win in wins[:12]:  # Show first 12
                    title = win["title"]
                    opponent = win["opponent"]
                    date = win["date"]
                    castle_result = win["castle_result"]
                    castle_detail = win["castle_detail"]
                    role = win["role"]
                    prep_result = win["prep_result"]

                    wins_text.append(
                        f"✅ **{title}** vs Kingdom {opponent}\n"
                        f"   ├─ {date} | {role}\n"
                        f"   ├─ {castle_result} {castle_detail}\n"
                        f"   └─ {prep_result}"
                    )

                wins_str = "\n".join(wins_text)
                if len(wins) > 12:
                    wins_str += f"\n*... and {len(wins) - 12} more victories*"

                embed.add_field(name=f"✅ Victories ({len(wins)})", value=wins_str, inline=False)

            # Add losses field
            if losses:
                losses_text = []
                for loss in losses[:12]:  # Show first 12
                    title = loss["title"]
                    opponent = loss["opponent"]
                    date = loss["date"]
                    castle_result = loss["castle_result"]
                    castle_detail = loss["castle_detail"]
                    role = loss["role"]
                    prep_result = loss["prep_result"]

                    losses_text.append(
                        f"❌ **{title}** vs Kingdom {opponent}\n"
                        f"   ├─ {date} | {role}\n"
                        f"   ├─ {castle_result} {castle_detail}\n"
                        f"   └─ {prep_result}"
                    )

                losses_str = "\n".join(losses_text)
                if len(losses) > 12:
                    losses_str += f"\n*... and {len(losses) - 12} more defeats*"

                embed.add_field(name=f"❌ Defeats ({len(losses)})", value=losses_str, inline=False)

            # Calculate win rate
            total = len(wins) + len(losses)
            win_rate = (len(wins) / total * 100) if total > 0 else 0
            embed.set_footer(
                text=f"Win Rate: {len(wins)}/{total} ({win_rate:.1f}%) | Data as of {result.get('timestamp', 'N/A')}"
            )

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully listed {len(matches)} KVK matches for kingdom {kingdom_number}")

        except Exception as e:
            logger.error(f"Error fetching KVK matches for kingdom {kingdom_number}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while fetching KVK matches. Please try again later.")
