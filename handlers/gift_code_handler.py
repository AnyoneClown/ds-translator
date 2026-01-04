import logging
from datetime import datetime, timezone
from typing import Dict, List

import discord
from discord import app_commands
from discord.ext import commands

from db import get_db
from services.database_service import DatabaseService
from services.gift_code_service import IGiftCodeService
from services.player_info_service import IPlayerInfoService

logger = logging.getLogger(__name__)


class GiftCodeHandler:
    """Handles gift code redemption Discord commands."""

    def __init__(
        self,
        gift_code_service: IGiftCodeService,
        player_info_service: IPlayerInfoService,
        bot: commands.Bot,
    ):
        """
        Initialize gift code handler.

        Args:
            gift_code_service: Service for redeeming gift codes
            player_info_service: Service for validating player existence
            bot: Discord bot instance
        """
        self._gift_code_service = gift_code_service
        self._player_info_service = player_info_service
        self._bot = bot
        logger.info("GiftCodeHandler initialized")

    def register_commands(self):
        """Register all gift code commands with the bot."""

        @self._bot.tree.command(name="redeem", description="Redeem a gift code for all registered players")
        @app_commands.describe(gift_code="The gift code to redeem (e.g., KINGSHOTXMAS)")
        async def redeem_gift_code(interaction: discord.Interaction, gift_code: str):
            """Redeem a gift code for all registered players."""
            await self._handle_redeem_gift_code_slash(interaction, gift_code)

        @self._bot.tree.command(name="giftcodes", description="List all available gift codes")
        async def list_gift_codes(interaction: discord.Interaction):
            """List all available gift codes."""
            await self._handle_list_gift_codes_slash(interaction)

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

        @self._bot.tree.command(name="toggleplayer", description="Enable/disable a player for gift code redemption")
        @app_commands.describe(player_id="The player ID to toggle")
        async def toggle_player(interaction: discord.Interaction, player_id: str):
            """Enable/disable a player for gift code redemption."""
            await self._handle_toggle_player_slash(interaction, player_id)

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
                                }
                            )
                            continue

                        player_id_int = int(player.player_id)
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
                            }
                        )

                # Format and send results
                await self._send_redemption_results_slash(interaction, gift_code, results)

        except Exception as e:
            logger.error(f"Error in bulk redemption: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An unexpected error occurred while processing the redemption. Please try again later."
            )

    async def _handle_list_gift_codes_slash(self, interaction: discord.Interaction):
        """
        Handle listing all available gift codes.

        Args:
            interaction: Discord interaction
        """
        await interaction.response.defer(thinking=True)

        user_info = f"{interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})"
        guild_info = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"

        logger.info(f"List gift codes command requested by {user_info} in {guild_info}")

        try:
            # Fetch gift codes from API
            result = await self._gift_code_service.get_available_gift_codes()

            if not result.get("success"):
                await interaction.followup.send(
                    "❌ Failed to fetch gift codes from the API.\n"
                    "Please try again later or contact an administrator."
                )
                logger.warning(f"Failed to fetch gift codes: {result.get('message')}")
                return

            data = result.get("data", {})
            gift_codes = data.get("giftCodes", [])
            total = data.get("total", 0)
            active_count = data.get("activeCount", 0)
            expired_count = data.get("expiredCount", 0)

            if not gift_codes:
                await interaction.followup.send("📭 No gift codes available at the moment.")
                return

            # Separate active and expired codes
            active_codes = []
            expired_codes = []

            for code in gift_codes:
                expires_at = code.get("expiresAt")
                if expires_at:
                    try:
                        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        if expires_dt > now:
                            active_codes.append(code)
                        else:
                            expired_codes.append(code)
                    except (ValueError, AttributeError):
                        # If parsing fails, treat as active
                        active_codes.append(code)
                else:
                    # No expiration date = permanent code
                    active_codes.append(code)

            # Create main embed
            embed = discord.Embed(
                title="🎁 Available Gift Codes",
                description=(f"**Total:** {total} | **Active:** {active_count} | **Expired:** {expired_count}"),
                color=discord.Color.gold(),
            )

            # Add active codes field
            if active_codes:
                active_text = []
                for code in active_codes[:15]:  # Show first 15
                    code_name = code.get("code", "UNKNOWN")
                    expires_at = code.get("expiresAt")

                    if expires_at:
                        try:
                            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                            # Format as relative time or specific date
                            expires_str = f"Expires: {expires_dt.strftime('%Y-%m-%d %H:%M UTC')}"
                        except (ValueError, AttributeError):
                            expires_str = "No expiration"
                    else:
                        expires_str = "Permanent 🔓"

                    active_text.append(f"✅ `{code_name}`\n   └─ {expires_str}")

                active_str = "\n".join(active_text)
                if len(active_codes) > 15:
                    active_str += f"\n*... and {len(active_codes) - 15} more*"

                embed.add_field(name=f"✅ Active ({len(active_codes)})", value=active_str, inline=False)

            # Add expired codes field (optional, show fewer)
            if expired_codes and len(expired_codes) <= 5:
                expired_text = []
                for code in expired_codes:
                    code_name = code.get("code", "UNKNOWN")
                    expired_text.append(f"⛔ `{code_name}`")

                expired_str = "\n".join(expired_text)
                embed.add_field(name=f"⛔ Expired ({len(expired_codes)})", value=expired_str, inline=False)
            elif expired_codes:
                embed.add_field(
                    name=f"⛔ Expired ({len(expired_codes)})",
                    value=f"*{len(expired_codes)} expired codes available*",
                    inline=False,
                )

            embed.set_footer(text="Use /redeem {code} to redeem a gift code for all your registered players")

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully listed {len(gift_codes)} gift codes for {user_info}")

        except Exception as e:
            logger.error(f"Error listing gift codes: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while fetching gift codes. Please try again later.")

    async def _send_redemption_results_slash(
        self,
        interaction: discord.Interaction,
        gift_code: str,
        results: List[Dict],
    ):
        """Send formatted redemption results."""
        success_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - success_count

        # Create embed
        if success_count == len(results):
            color = discord.Color.green()
            title = "✅ All Gift Codes Redeemed Successfully!"
        elif success_count > 0:
            color = discord.Color.gold()
            title = "⚠️ Gift Codes Partially Redeemed"
        else:
            color = discord.Color.red()
            title = "❌ All Gift Code Redemptions Failed"

        embed = discord.Embed(
            title=title,
            description=f"**Gift Code:** `{gift_code}`\n"
            f"**Success:** {success_count}/{len(results)} | **Failed:** {failed_count}/{len(results)}",
            color=color,
        )

        # Add successful redemptions
        if success_count > 0:
            success_text = []
            for r in results:
                if r["success"]:
                    player_display = r["player_name"] or r["player_id"]
                    success_text.append(f"✅ `{r['player_id']}` - {player_display}")

            if success_text:
                # Split into chunks if too long
                success_str = "\n".join(success_text[:10])
                if len(success_text) > 10:
                    success_str += f"\n*... and {len(success_text) - 10} more*"
                embed.add_field(name="✅ Successful", value=success_str, inline=False)

        # Add failed redemptions
        if failed_count > 0:
            failed_text = []
            for r in results:
                if not r["success"]:
                    player_display = r["player_name"] or r["player_id"]
                    error_info = r.get("message", "UNKNOWN")
                    failed_text.append(f"❌ `{r['player_id']}` - {player_display}\n   └─ {error_info}")

            if failed_text:
                # Split into chunks if too long
                failed_str = "\n".join(failed_text[:10])
                if len(failed_text) > 10:
                    failed_str += f"\n*... and {len(failed_text) - 10} more*"
                embed.add_field(name="❌ Failed", value=failed_str, inline=False)

        embed.set_footer(text="🎮 Check in-game mail for successfully redeemed codes!")

        await interaction.followup.send(embed=embed)
        logger.info(f"Bulk redemption completed: {success_count} successful, {failed_count} failed")

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

                embed = discord.Embed(
                    title="📋 Registered Players for Gift Code Redemption",
                    description=f"**Total:** {len(all_players)} | **Enabled:** {len(enabled_players)} | **Disabled:** {len(disabled_players)}",
                    color=discord.Color.blue(),
                )

                if enabled_players:
                    enabled_text = []
                    for p in enabled_players[:15]:
                        display = f"`{p.player_id}`"
                        if p.player_name:
                            display += f" - {p.player_name}"
                        enabled_text.append(f"✅ {display}")

                    enabled_str = "\n".join(enabled_text)
                    if len(enabled_players) > 15:
                        enabled_str += f"\n*... and {len(enabled_players) - 15} more*"
                    embed.add_field(name="✅ Enabled", value=enabled_str, inline=False)

                if disabled_players:
                    disabled_text = []
                    for p in disabled_players[:10]:
                        display = f"`{p.player_id}`"
                        if p.player_name:
                            display += f" - {p.player_name}"
                        disabled_text.append(f"⛔ {display}")

                    disabled_str = "\n".join(disabled_text)
                    if len(disabled_players) > 10:
                        disabled_str += f"\n*... and {len(disabled_players) - 10} more*"
                    embed.add_field(name="⛔ Disabled", value=disabled_str, inline=False)

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
