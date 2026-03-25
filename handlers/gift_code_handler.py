import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config.bot_config import BotConfig
from db import get_db
from services.database_service import DatabaseService
from services.gift_code_service import IGiftCodeService
from services.player_info_service import IPlayerInfoService

logger = logging.getLogger(__name__)


class GiftCodeHandler:
    """Handles gift code redemption Discord commands."""

    STATUS_SUCCESS = "success"
    STATUS_ALREADY_REDEEMED = "already_redeemed"
    STATUS_API_REJECTED = "api_rejected"
    STATUS_INVALID_ID = "invalid_id"

    def __init__(
        self,
        gift_code_service: IGiftCodeService,
        player_info_service: IPlayerInfoService,
        bot: commands.Bot,
        config: BotConfig,
    ):
        """
        Initialize gift code handler.

        Args:
            gift_code_service: Service for redeeming gift codes
            player_info_service: Service for validating player existence
            bot: Discord bot instance
            config: Bot configuration
        """
        self._gift_code_service = gift_code_service
        self._player_info_service = player_info_service
        self._bot = bot
        self._config = config
        logger.info("GiftCodeHandler initialized")

    def register_commands(self):
        """Register all gift code commands with the bot."""

        @self._bot.tree.command(name="redeem", description="Redeem a gift code for all registered players")
        @app_commands.describe(gift_code="The gift code to redeem (e.g., KINGSHOTXMAS)")
        async def redeem_gift_code(interaction: discord.Interaction, gift_code: str):
            """Redeem a gift code for all registered players."""
            await self._handle_redeem_gift_code_slash(interaction, gift_code)

        @self._bot.tree.command(name="addplayer", description="Add a player to gift code redemption list")
        @app_commands.describe(player_id="The player ID (API name) to add")
        async def add_player(interaction: discord.Interaction, player_id: str):
            """Add a player to gift code list using API name."""
            await self._handle_add_player_slash(interaction, player_id)

        @self._bot.tree.command(name="removeplayer", description="Remove a player from gift code redemption list")
        @app_commands.describe(player_id="The player ID to remove")
        async def remove_player(interaction: discord.Interaction, player_id: str):
            """Remove a player from gift code redemption list."""
            await self._handle_remove_player_slash(interaction, player_id)

        @self._bot.tree.command(name="listplayers", description="List all registered players for gift code redemption")
        async def list_players(interaction: discord.Interaction):
            """List all registered players for gift code redemption."""
            await self._handle_list_players_slash(interaction)

        @self._bot.tree.command(name="giftcodes", description="List available gift codes")
        async def list_giftcodes(interaction: discord.Interaction):
            """List available gift codes from the API."""
            await self._handle_list_gift_codes_slash(interaction)

        @self._bot.tree.command(name="toggleplayer", description="Enable/disable a player for gift code redemption")
        @app_commands.describe(player_id="The player ID to toggle")
        async def toggle_player(interaction: discord.Interaction, player_id: str):
            """Enable/disable a player for gift code redemption."""
            await self._handle_toggle_player_slash(interaction, player_id)

    def start_polling_task(self):
        """Start the background task that checks for new gift codes."""

        @tasks.loop(minutes=10)
        async def poll_gift_codes():
            """Check for new gift codes and redeem them for all users."""
            logger.info("Polling for new gift codes...")

            try:
                # Fetch available codes from 3rd party API
                response = await self._gift_code_service.get_available_gift_codes()
                if not response.get("success"):
                    logger.warning(f"Failed to poll gift codes: {response.get('message')}")
                    return

                codes = response.get("data", [])
                if not codes:
                    return

                db = get_db()
                async with db.session() as session:
                    # Check which codes are new
                    new_codes_found = []

                    for row in codes:
                        code_id = row.get("id")
                        code_str = row.get("code")

                        if not code_id or not code_str:
                            continue

                        # Parse dates
                        created_at_api = row.get("createdAt")
                        expires_at = row.get("expiresAt")

                        try:
                            # Parse ISO format datetime strings
                            dt_created = (
                                datetime.fromisoformat(created_at_api.replace("Z", "+00:00"))
                                if created_at_api
                                else datetime.now(timezone.utc)
                            )
                            dt_expires = (
                                datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if expires_at else None
                            )

                            is_new, _ = await DatabaseService.add_or_update_gift_code(
                                session, code_id, code_str, dt_created, dt_expires
                            )

                            if is_new:
                                new_codes_found.append(code_str)

                        except ValueError as e:
                            logger.error(f"Error parsing date for gift code {code_str}: {e}")

                    # If we found new codes, redeem them!
                    if new_codes_found:
                        logger.info(f"Found {len(new_codes_found)} new gift codes. Starting auto-redemption...")

                        # Ensure the bot user exists in the database to satisfy the foreign key constraint
                        bot_user_id = self._bot.user.id if self._bot.user else 0
                        bot_username = self._bot.user.name if self._bot.user else "System Bot"
                        bot_discriminator = (
                            getattr(self._bot.user, "discriminator", "0000") if self._bot.user else "0000"
                        )
                        bot_display_name = (
                            getattr(self._bot.user, "display_name", "System Bot") if self._bot.user else "System Bot"
                        )

                        await DatabaseService.get_or_create_user(
                            session,
                            bot_user_id,
                            bot_username,
                            bot_discriminator,
                            bot_display_name,
                        )

                        # Get all enabled players
                        registered_players = await DatabaseService.get_registered_players(session, enabled_only=True)

                        if not registered_players:
                            logger.info("No registered players to auto-redeem for.")
                            return

                        # Redeem each code for each player
                        for new_code in new_codes_found:
                            logger.info(f"Auto-redeeming code '{new_code}' for {len(registered_players)} players...")

                            # Fetch already redeemed set specific to this code to minimize lookups
                            already_redeemed = await self._gift_code_service.get_redeemed_players(session, new_code)

                            # Track results for this specific code
                            success_count = 0
                            already_redeemed_count = 0
                            api_rejected_count = 0
                            invalid_id_count = 0

                            for player in registered_players:
                                if player.player_id in already_redeemed:
                                    already_redeemed_count += 1
                                    continue

                                try:
                                    player_id_int = int(player.player_id)

                                    # Add jitter to avoid rating limits
                                    await asyncio.sleep(1.0)

                                    result = await self._gift_code_service.redeem_gift_code(
                                        session, player_id_int, new_code
                                    )

                                    # Track detailed status category
                                    status_category = self._categorize_redemption_status(result)
                                    if status_category == self.STATUS_SUCCESS:
                                        success_count += 1
                                    elif status_category == self.STATUS_ALREADY_REDEEMED:
                                        already_redeemed_count += 1
                                    elif status_category == self.STATUS_INVALID_ID:
                                        invalid_id_count += 1
                                    else:
                                        api_rejected_count += 1

                                    # We need a system bot user ID since there is no interaction context
                                    # We use the bot's user ID
                                    bot_user_id = self._bot.user.id if self._bot.user else 0

                                    await DatabaseService.log_gift_code_redemption(
                                        session,
                                        user_id=bot_user_id,
                                        player_id=player.player_id,
                                        gift_code=new_code,
                                        success=result.get("success", False),
                                        response_message=result.get("message"),
                                        error_code=result.get("error_code"),
                                    )

                                except ValueError:
                                    logger.error(f"Invalid player ID format during auto-redeem: {player.player_id}")
                                    invalid_id_count += 1
                                except Exception as e:
                                    logger.error(f"Error auto-redeeming {new_code} for {player.player_id}: {e}")
                                    api_rejected_count += 1

                            # Send Discord announcement if channels are configured
                            if self._config.auto_redeem_channels:
                                embed = discord.Embed(
                                    title="🎁 New Gift Code Found!",
                                    description="Auto-redemption triggered for newly discovered gift code.",
                                    color=discord.Color.brand_green(),
                                )
                                embed.add_field(name="Gift Code", value=f"`{new_code}`", inline=False)
                                embed.add_field(
                                    name="Auto-Redeem Status",
                                    value=(
                                        f"✅ **Success**: {success_count}\n"
                                        f"🔄 **Already Claimed**: {already_redeemed_count}\n"
                                        f"🚫 **API Rejected**: {api_rejected_count}\n"
                                        f"🆔 **Invalid ID**: {invalid_id_count}\n"
                                        f"👥 **Total Players**: {len(registered_players)}"
                                    ),
                                    inline=False,
                                )
                                embed.set_footer(text="Check in-game mail for successfully redeemed codes!")

                                for channel_id in self._config.auto_redeem_channels:
                                    channel = self._bot.get_channel(channel_id)
                                    if channel and isinstance(channel, discord.TextChannel):
                                        try:
                                            await channel.send(embed=embed)
                                            logger.info(f"Announced gift code {new_code} in channel {channel_id}")
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to send gift code announcement to channel {channel_id}: {e}"
                                            )
                                    else:
                                        logger.warning(
                                            f"Configured auto-redeem channel {channel_id} not found or is not a text channel"
                                        )

            except Exception as e:
                logger.error(f"Error in poll_gift_codes background task: {e}")

        # Wait until bot is fully ready before running the loop
        @poll_gift_codes.before_loop
        async def before_polling():
            logger.info("Waiting for bot to be ready before starting gift code polling...")
            await self._bot.wait_until_ready()

        poll_gift_codes.start()

    async def _handle_list_gift_codes_slash(self, interaction: discord.Interaction):
        """Handle listing available gift codes."""
        await interaction.response.defer(thinking=True)

        try:
            response = await self._gift_code_service.get_available_gift_codes()

            if not response.get("success"):
                await interaction.followup.send(f"❌ Failed to fetch gift codes: {response.get('message')}")
                return

            codes = response.get("data", [])

            if not codes:
                await interaction.followup.send("📋 No active gift codes found.")
                return

            embed = discord.Embed(
                title="🎁 Active Gift Codes",
                description="List of available gift codes to redeem",
                color=discord.Color.green(),
            )

            for code in codes:
                code_str = code.get("code", "UNKNOWN")
                expires_at = code.get("expiresAt")

                value = "`" + code_str + "`"
                if expires_at:
                    try:
                        # Attempt to parse ISO string and format
                        dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        value += f"\nExpires: <t:{int(dt.timestamp())}:R>"
                    except ValueError:
                        value += f"\nExpires: {expires_at}"
                else:
                    value += "\nNo expiration"

                embed.add_field(name="Gift Code", value=value, inline=False)

            embed.set_footer(text="Use /redeem to run manual redemptions or wait for auto-redeem")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing gift codes: {e}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred while fetching gift codes.")

    async def _handle_redeem_gift_code_slash(self, interaction: discord.Interaction, gift_code: str):
        """
        Handle the redeem command for all registered players.

        Args:
            interaction: Discord interaction
            gift_code: The gift code to redeem
        """
        await interaction.response.defer(thinking=True)

        user_info = f"{interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})"
        guild_info = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"

        logger.info(f"Bulk redeem command for code '{gift_code}' requested by {user_info} in {guild_info}")

        # Get all registered players
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

                registered_players = await DatabaseService.get_registered_players(session, enabled_only=True)

                if not registered_players:
                    await interaction.followup.send(
                        "❌ No registered players found. Use `/addplayer {player_id}` to add players first."
                    )
                    return

                # Get all players who have already redeemed this code (single DB query)
                already_redeemed = await self._gift_code_service.get_redeemed_players(session, gift_code)
                logger.info(f"Found {len(already_redeemed)} players who already redeemed code '{gift_code}'")

                # Redeem for each player
                results = []
                for player in registered_players:
                    try:
                        # Check if already redeemed (in-memory check, not DB query)
                        if player.player_id in already_redeemed:
                            logger.info(
                                f"Skipping gift code '{gift_code}' for player {player.player_id} - already redeemed"
                            )
                            results.append(
                                {
                                    "player_id": player.player_id,
                                    "player_name": player.player_name,
                                    "success": False,
                                    "message": "Already redeemed",
                                    "error_code": "ALREADY_REDEEMED",
                                    "already_redeemed": True,
                                    "status_category": self.STATUS_ALREADY_REDEEMED,
                                }
                            )
                            continue

                        player_id_int = int(player.player_id)

                        # Add jitter/delay to prevent 429 Too Many Requests from bulk redemption
                        if len(results) > 0:
                            await asyncio.sleep(1.0)

                        result = await self._gift_code_service.redeem_gift_code(session, player_id_int, gift_code)

                        # Log to database
                        await DatabaseService.log_gift_code_redemption(
                            session,
                            user_id=interaction.user.id,
                            player_id=player.player_id,
                            gift_code=gift_code,
                            success=result.get("success", False),
                            response_message=result.get("message"),
                            error_code=result.get("error_code"),
                            guild_id=interaction.guild.id if interaction.guild else None,
                            channel_id=interaction.channel.id,
                        )

                        results.append(
                            {
                                "player_id": player.player_id,
                                "player_name": player.player_name,
                                "success": result.get("success", False),
                                "message": result.get("message", "Unknown error"),
                                "error_code": result.get("error_code"),
                                "already_redeemed": result.get("already_redeemed", False),
                                "status_category": self._categorize_redemption_status(result),
                            }
                        )
                    except ValueError:
                        logger.error(f"Invalid player ID format: {player.player_id}")
                        results.append(
                            {
                                "player_id": player.player_id,
                                "player_name": player.player_name,
                                "success": False,
                                "message": "Invalid player ID format",
                                "error_code": "INVALID_ID",
                                "status_category": self.STATUS_INVALID_ID,
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error redeeming for player {player.player_id}: {e}")
                        results.append(
                            {
                                "player_id": player.player_id,
                                "player_name": player.player_name,
                                "success": False,
                                "message": "Unexpected error occurred",
                                "error_code": "UNKNOWN_ERROR",
                                "status_category": self.STATUS_API_REJECTED,
                            }
                        )

                # Format and send results
                await self._send_redemption_results_slash(interaction, gift_code, results)

        except Exception as e:
            logger.error(f"Error in bulk redemption: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An unexpected error occurred while processing the redemption. Please try again later."
            )

    async def _send_redemption_results_slash(
        self,
        interaction: discord.Interaction,
        gift_code: str,
        results: List[Dict],
    ):
        """Send formatted redemption results."""
        success_results = [r for r in results if r.get("status_category") == self.STATUS_SUCCESS]
        already_redeemed_results = [r for r in results if r.get("status_category") == self.STATUS_ALREADY_REDEEMED]
        api_rejected_results = [r for r in results if r.get("status_category") == self.STATUS_API_REJECTED]
        invalid_id_results = [r for r in results if r.get("status_category") == self.STATUS_INVALID_ID]

        success_count = len(success_results)
        already_redeemed_count = len(already_redeemed_results)
        api_rejected_count = len(api_rejected_results)
        invalid_id_count = len(invalid_id_results)
        total_count = len(results)

        # Create embed
        if success_count == total_count:
            color = discord.Color.green()
            title = "✅ All Gift Codes Redeemed Successfully!"
        elif success_count > 0:
            color = discord.Color.gold()
            title = "⚠️ Gift Code Redemption Completed"
        else:
            color = discord.Color.red()
            title = "❌ All Gift Code Redemptions Failed"

        embed = discord.Embed(
            title=title,
            description=f"**Gift Code:** `{gift_code}`\n"
            f"**✅ Success:** {success_count}/{total_count}\n"
            f"**🔄 Already Redeemed:** {already_redeemed_count}/{total_count}\n"
            f"**🚫 API Rejected:** {api_rejected_count}/{total_count}\n"
            f"**🆔 Invalid ID:** {invalid_id_count}/{total_count}",
            color=color,
        )

        if success_results:
            embed.add_field(
                name="✅ Success",
                value=self._format_result_lines(success_results, "✅"),
                inline=False,
            )

        if already_redeemed_results:
            embed.add_field(
                name="🔄 Already Redeemed",
                value=self._format_result_lines(already_redeemed_results, "🔄"),
                inline=False,
            )

        if api_rejected_results:
            embed.add_field(
                name="🚫 API Rejected",
                value=self._format_result_lines(api_rejected_results, "🚫"),
                inline=False,
            )

        if invalid_id_results:
            embed.add_field(
                name="🆔 Invalid ID",
                value=self._format_result_lines(invalid_id_results, "🆔"),
                inline=False,
            )

        embed.set_footer(text="🎮 Check in-game mail for successfully redeemed codes!")

        await interaction.followup.send(embed=embed)
        logger.info(
            "Bulk redemption completed: success=%s, already_redeemed=%s, api_rejected=%s, invalid_id=%s",
            success_count,
            already_redeemed_count,
            api_rejected_count,
            invalid_id_count,
        )

    def _categorize_redemption_status(self, result: Dict) -> str:
        """Map API/database redemption result into a single status category."""
        if result.get("success", False):
            return self.STATUS_SUCCESS

        if (
            result.get("already_redeemed", False)
            or result.get("already_redeemed_by_api", False)
            or result.get("error_code") in {"ALREADY_REDEEMED", "ALREADY_REDEEMED_BY_API"}
        ):
            return self.STATUS_ALREADY_REDEEMED

        if result.get("error_code") in {"INVALID_ID", "INVALID_USER_ID", "INVALID_PLAYER_ID"}:
            return self.STATUS_INVALID_ID

        return self.STATUS_API_REJECTED

    def _format_result_lines(self, records: List[Dict], emoji: str, limit: int = 10) -> str:
        """Render result records for embed fields with deterministic truncation."""
        lines = []
        for record in records[:limit]:
            player_display = record.get("player_name") or record.get("player_id")
            message = record.get("message", "No details")
            lines.append(f"{emoji} `{record['player_id']}` - {player_display}\n   └─ {message}")

        if len(records) > limit:
            lines.append(f"*... and {len(records) - limit} more*")

        return "\n".join(lines)

    def _build_player_lines(self, players: List) -> List[str]:
        """Format registered players for paginated display."""
        lines = []
        for player in players:
            status = "✅" if player.enabled else "⛔"
            line = f"{status} `{player.player_id}`"
            if player.player_name:
                line += f" - {player.player_name}"
            lines.append(line)
        return lines

    def _chunk_lines(self, lines: List[str], page_size: int) -> List[List[str]]:
        """Split lines into fixed-size pages."""
        return [lines[idx : idx + page_size] for idx in range(0, len(lines), page_size)]

    async def _handle_add_player_slash(self, interaction: discord.Interaction, player_id: str):
        """Handle adding a player to the redemption list."""
        await interaction.response.defer(thinking=True)

        try:
            # Validate player exists via PlayerInfoService
            player_info = await self._player_info_service.get_player_info(player_id)
            if player_info is None:
                embed = discord.Embed(
                    title="❌ Player Not Found",
                    description=(
                        f"Could not find a player with ID `{player_id}`.\n"
                        f"Please verify the ID in-game and try again."
                    ),
                    color=discord.Color.red(),
                )
                await interaction.followup.send(embed=embed)
                logger.warning(f"Attempt to add non-existent player ID {player_id}")
                return

            db = get_db()
            async with db.session() as session:
                await DatabaseService.get_or_create_user(
                    session,
                    interaction.user.id,
                    interaction.user.name,
                    interaction.user.discriminator,
                    interaction.user.display_name,
                )

                # Use API-provided name only
                resolved_name = player_info.get("name")

                await DatabaseService.add_registered_player(
                    session,
                    player_id=player_id,
                    added_by_user_id=interaction.user.id,
                    player_name=resolved_name,
                    enabled=True,
                )

                embed = discord.Embed(
                    title="✅ Player Added Successfully",
                    description="Player has been added to the gift code redemption list.",
                    color=discord.Color.green(),
                )
                embed.add_field(name="Player ID", value=f"`{player_id}`", inline=True)
                if resolved_name:
                    embed.add_field(name="Player Name", value=resolved_name, inline=True)
                embed.add_field(name="Status", value="✅ Enabled", inline=True)

                await interaction.followup.send(embed=embed)
                logger.info(f"Player {player_id} added by {interaction.user.id}")

        except Exception as e:
            logger.error(f"Error adding player {player_id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while adding the player.")

    async def _handle_remove_player_slash(self, interaction: discord.Interaction, player_id: str):
        """Handle removing a player from the redemption list."""
        await interaction.response.defer(thinking=True)

        try:
            db = get_db()
            async with db.session() as session:
                # Fetch player to check ownership
                player = await DatabaseService.get_registered_player(session, player_id)

                if not player:
                    await interaction.followup.send(f"❌ Player `{player_id}` not found in the redemption list.")
                    return

                # Determine admin status (guild context only)
                is_admin = False
                if interaction.guild and interaction.user.guild_permissions:
                    is_admin = bool(interaction.user.guild_permissions.administrator)

                # Check ownership or admin rights
                if player.added_by_user_id != interaction.user.id and not is_admin:
                    await interaction.followup.send(
                        "⛔ You can only remove players that you added, or you must be an admin."
                    )
                    return

                # Proceed with removal
                removed = await DatabaseService.remove_registered_player(session, player_id)

                if removed:
                    embed = discord.Embed(
                        title="✅ Player Removed",
                        description=f"Player `{player_id}` has been removed from the gift code redemption list.",
                        color=discord.Color.green(),
                    )
                    await interaction.followup.send(embed=embed)
                    logger.info(f"Player {player_id} removed by {interaction.user.id} (admin={is_admin})")
                else:
                    await interaction.followup.send(f"❌ Player `{player_id}` not found in the redemption list.")

        except Exception as e:
            logger.error(f"Error removing player {player_id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while removing the player.")

    async def _handle_list_players_slash(self, interaction: discord.Interaction):
        """Handle listing all registered players."""
        await interaction.response.defer(thinking=True)

        try:
            db = get_db()
            async with db.session() as session:
                all_players = await DatabaseService.get_registered_players(session, enabled_only=False)

                if not all_players:
                    await interaction.followup.send("📋 No players registered for gift code redemption.")
                    return

                enabled_players = [p for p in all_players if p.enabled]
                disabled_players = [p for p in all_players if not p.enabled]
                ordered_players = enabled_players + disabled_players
                player_lines = self._build_player_lines(ordered_players)
                pages = self._chunk_lines(player_lines, page_size=20)

                for page_number, page_lines in enumerate(pages, start=1):
                    embed = discord.Embed(
                        title="📋 Registered Players for Gift Code Redemption",
                        description=(
                            f"**Total:** {len(all_players)} | **Enabled:** {len(enabled_players)} | "
                            f"**Disabled:** {len(disabled_players)}\n"
                            f"**Page:** {page_number}/{len(pages)}"
                        ),
                        color=discord.Color.blue(),
                    )
                    embed.add_field(name="Players", value="\n".join(page_lines), inline=False)

                    await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing players: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while retrieving the player list.")

    async def _handle_toggle_player_slash(self, interaction: discord.Interaction, player_id: str):
        """Handle toggling a player's enabled status."""
        await interaction.response.defer(thinking=True)

        try:
            db = get_db()
            async with db.session() as session:
                new_status = await DatabaseService.toggle_registered_player(session, player_id)

                if new_status is not None:
                    status_emoji = "✅" if new_status else "⛔"
                    status_text = "enabled" if new_status else "disabled"

                    embed = discord.Embed(
                        title=f"{status_emoji} Player Status Updated",
                        description=f"Player `{player_id}` has been **{status_text}** for gift code redemption.",
                        color=(discord.Color.green() if new_status else discord.Color.orange()),
                    )
                    await interaction.followup.send(embed=embed)
                    logger.info(f"Player {player_id} toggled to {status_text} by {interaction.user.id}")
                else:
                    await interaction.followup.send(f"❌ Player `{player_id}` not found in the redemption list.")

        except Exception as e:
            logger.error(f"Error toggling player {player_id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while updating the player status.")
