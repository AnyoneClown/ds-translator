import logging
from typing import Any, Dict

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

        @self._bot.tree.command(name="kvk", description="Get Nexus KVK stats for a kingdom")
        @app_commands.describe(kingdom_number="The kingdom number to fetch stats for (e.g., 830)")
        async def get_kvk_stats(interaction: discord.Interaction, kingdom_number: int):
            """Get Nexus KVK stats for a kingdom."""
            await self._handle_get_kvk_stats_slash(interaction, kingdom_number)

        @self._bot.tree.command(name="kvk_compare", description="Compare Nexus KVK stats for two kingdoms")
        @app_commands.describe(
            kingdom_a="First kingdom number to compare",
            kingdom_b="Second kingdom number to compare",
        )
        async def compare_kvk_stats(interaction: discord.Interaction, kingdom_a: int, kingdom_b: int):
            """Compare Nexus KVK stats for two kingdoms."""
            await self._handle_compare_kvk_slash(interaction, kingdom_a, kingdom_b)

    async def _handle_get_kvk_stats_slash(self, interaction: discord.Interaction, kingdom_number: int):
        """
        Handle fetching Nexus KVK stats for a kingdom.

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

        logger.info(f"KVK stats requested for kingdom {kingdom_number} by {user_info} in {guild_info}")

        try:
            result = await self._kvk_service.get_kingdom_stats(kingdom_number)

            if not result.get("success"):
                await interaction.followup.send(
                    f"❌ Failed to fetch KVK stats for Kingdom {kingdom_number}.\n"
                    f"**Error:** {result.get('message', 'Unknown error')}"
                )
                logger.warning(f"Failed to fetch KVK stats for kingdom {kingdom_number}: {result.get('message')}")
                return

            stats = result.get("data", {})
            history = stats.get("history", [])
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            total = wins + losses
            computed_win_rate = (wins / total * 100) if total > 0 else 0
            win_rate = stats.get("winRate", computed_win_rate)

            embed = discord.Embed(
                title=f"⚔️ Nexus KVK - Kingdom {kingdom_number}",
                description=(
                    f"Tier: **{stats.get('nexusTier', 'N/A')}** | "
                    f"Stability: **{stats.get('stabilityLabel', 'N/A').title()}**"
                ),
                color=discord.Color.red(),
            )

            embed.add_field(name="Rank", value=f"#{stats.get('rank', 'N/A')}", inline=True)
            embed.add_field(name="Rating", value=f"{self._format_float(stats.get('rating'))}", inline=True)
            embed.add_field(name="Percentile", value=f"{self._format_float(stats.get('percentile'))}%", inline=True)
            embed.add_field(name="Matches", value=str(stats.get("matchCount", total)), inline=True)
            embed.add_field(name="W/L", value=f"{wins}/{losses}", inline=True)
            embed.add_field(name="Win Rate", value=f"{self._format_float(win_rate)}%", inline=True)

            if history:
                history_lines = []
                for entry in history[:8]:
                    kvk_number = entry.get("kvk", "?")
                    opponent = entry.get("opponent", "?")
                    result_text = self._format_history_result(entry.get("result"))
                    rating_change = self._format_signed_float(entry.get("ratingChange"))
                    history_lines.append(
                        f"KvK {kvk_number}: vs {opponent} | {result_text} | Rating {rating_change}"
                    )

                embed.add_field(
                    name="Recent History",
                    value="\n".join(history_lines),
                    inline=False,
                )

            embed.set_footer(text=f"RD: {self._format_float(stats.get('rd'))} | Volatility: {self._format_float(stats.get('vol'))}")

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully sent KVK stats for kingdom {kingdom_number}")

        except Exception as e:
            logger.error(f"Error fetching KVK stats for kingdom {kingdom_number}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while fetching KVK stats. Please try again later.")

    async def _handle_compare_kvk_slash(self, interaction: discord.Interaction, kingdom_a: int, kingdom_b: int):
        """Handle comparing Nexus KVK stats for two kingdoms."""
        await interaction.response.defer(thinking=True)

        if kingdom_a <= 0 or kingdom_b <= 0:
            await interaction.followup.send("❌ Kingdom numbers must be positive integers.")
            return

        if kingdom_a == kingdom_b:
            await interaction.followup.send("❌ Please provide two different kingdoms to compare.")
            return

        logger.info(f"KVK comparison requested for kingdoms {kingdom_a} vs {kingdom_b}")

        try:
            result = await self._kvk_service.compare_kingdoms(kingdom_a, kingdom_b)
            if not result.get("success"):
                await interaction.followup.send(
                    "❌ Failed to compare kingdoms.\n"
                    f"**Error:** {result.get('message', 'Unknown error')}"
                )
                return

            data = result.get("data", {})
            stats_a = data.get("kingdom_a", {})
            stats_b = data.get("kingdom_b", {})
            score = data.get("score", {})

            score_a = score.get(str(kingdom_a), 0)
            score_b = score.get(str(kingdom_b), 0)

            if score_a > score_b:
                verdict = f"Kingdom {kingdom_a} leads ({score_a}-{score_b})"
            elif score_b > score_a:
                verdict = f"Kingdom {kingdom_b} leads ({score_b}-{score_a})"
            else:
                verdict = f"Dead heat ({score_a}-{score_b})"

            embed = discord.Embed(
                title=f"⚔️ KvK Compare: {kingdom_a} vs {kingdom_b}",
                description=verdict,
                color=discord.Color.gold(),
            )

            embed.add_field(
                name=f"Kingdom {kingdom_a}",
                value=self._build_compact_stats(stats_a),
                inline=True,
            )
            embed.add_field(
                name=f"Kingdom {kingdom_b}",
                value=self._build_compact_stats(stats_b),
                inline=True,
            )

            metrics = [
                ("Rating", stats_a.get("rating"), stats_b.get("rating")),
                ("Rank", stats_a.get("rank"), stats_b.get("rank")),
                ("Win Rate", stats_a.get("winRate"), stats_b.get("winRate")),
                ("Wins", stats_a.get("wins"), stats_b.get("wins")),
                ("Losses", stats_a.get("losses"), stats_b.get("losses")),
                ("Percentile", stats_a.get("percentile"), stats_b.get("percentile")),
            ]

            comparison_lines = []
            for metric, value_a, value_b in metrics:
                comparison_lines.append(
                    f"{metric}: {self._format_metric(metric, value_a)} vs {self._format_metric(metric, value_b)}"
                )

            embed.add_field(name="Head-to-Head Metrics", value="\n".join(comparison_lines), inline=False)

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully compared kingdoms {kingdom_a} and {kingdom_b}")
        except Exception as e:
            logger.error(f"Error comparing kingdoms {kingdom_a} vs {kingdom_b}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while comparing kingdoms. Please try again later.")

    @staticmethod
    def _format_float(value: Any) -> str:
        """Format numbers with two decimals when possible."""
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "N/A"

    @staticmethod
    def _format_signed_float(value: Any) -> str:
        """Format signed numeric values with two decimals."""
        try:
            return f"{float(value):+,.2f}"
        except (TypeError, ValueError):
            return "N/A"

    def _build_compact_stats(self, stats: Dict[str, Any]) -> str:
        """Build compact per-kingdom comparison lines."""
        return (
            f"Tier: {stats.get('nexusTier', 'N/A')}\n"
            f"Rank: #{stats.get('rank', 'N/A')}\n"
            f"Rating: {self._format_float(stats.get('rating'))}\n"
            f"W/L: {stats.get('wins', 'N/A')}/{stats.get('losses', 'N/A')}\n"
            f"Win Rate: {self._format_float(stats.get('winRate'))}%"
        )

    def _format_metric(self, metric: str, value: Any) -> str:
        """Format metric values for compare output."""
        if metric in {"Rating", "Percentile", "Win Rate"}:
            suffix = "%" if metric in {"Percentile", "Win Rate"} else ""
            return f"{self._format_float(value)}{suffix}"
        if metric == "Rank":
            return f"#{value}" if value is not None else "N/A"
        return str(value) if value is not None else "N/A"

    @staticmethod
    def _format_history_result(result: Any) -> str:
        """Normalize history result labels from Nexus API."""
        normalized = str(result or "Unknown").strip().lower()
        if normalized == "preparation":
            return "Preparation (Prep Win, Battle Loss)"
        if normalized == "win":
            return "Win"
        if normalized == "loss":
            return "Loss"
        return str(result or "Unknown")
