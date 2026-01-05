"""Handler for OCR Discord commands."""

import logging
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from db import get_db
from db.models import OCRRequest, OCRResult
from services.database_service import DatabaseService
from services.ocr_service import IOCRService

logger = logging.getLogger(__name__)


class OCRHandler:
    """Handles OCR Discord commands."""

    def __init__(self, ocr_service: IOCRService, bot: commands.Bot):
        """
        Initialize OCR handler.

        Args:
            ocr_service: Service for OCR processing
            bot: Discord bot instance
        """
        self._ocr_service = ocr_service
        self._bot = bot
        logger.info("OCRHandler initialized")

    def register_commands(self):
        """Register all OCR commands with the bot."""

        @self._bot.tree.command(name="ocr", description="Extract structured data from game screenshots")
        @app_commands.describe(
            ocr_type="Type of data to extract",
            image1="First screenshot (required)",
            image2="Second screenshot (optional)",
            image3="Third screenshot (optional)",
            image4="Fourth screenshot (optional)",
            image5="Fifth screenshot (optional)"
        )
        @app_commands.choices(ocr_type=[
            app_commands.Choice(name="Alliance Ranking", value="alliance-ranking"),
            app_commands.Choice(name="Kingdom Power Ranking", value="kingdom-power-ranking"),
            app_commands.Choice(name="KVK Points", value="kvk-points"),
            app_commands.Choice(name="Alliance Members", value="alliance-members"),
        ])
        async def ocr_command(
            interaction: discord.Interaction,
            ocr_type: str,
            image1: discord.Attachment,
            image2: discord.Attachment = None,
            image3: discord.Attachment = None,
            image4: discord.Attachment = None,
            image5: discord.Attachment = None
        ):
            """Extract structured data from game screenshots."""
            attachments = [image1]
            if image2:
                attachments.append(image2)
            if image3:
                attachments.append(image3)
            if image4:
                attachments.append(image4)
            if image5:
                attachments.append(image5)
            
            await self._handle_ocr_command(interaction, ocr_type, attachments)

    async def _handle_ocr_command(self, interaction: discord.Interaction, ocr_type: str, attachments: list):
        """
        Handle the OCR command.

        Args:
            interaction: Discord interaction
            ocr_type: Type of OCR extraction
            attachments: List of Discord attachments
        """
        await interaction.response.defer(thinking=True)

        user_info = f"{interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})"
        guild_info = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"
        
        logger.info(f"OCR command invoked by {user_info} in {guild_info} with type: {ocr_type}")

        # Filter for image attachments
        image_attachments = [
            att for att in attachments
            if att.content_type and att.content_type.startswith('image/')
        ]

        if not image_attachments:
            await interaction.followup.send(
                f"❌ No valid image attachments found! Found {len(attachments)} non-image attachment(s).\n"
                "Please attach PNG, JPG, or other image files.",
                ephemeral=True
            )
            return

        logger.info(f"Processing {len(image_attachments)} image(s)")

        # Download all images
        try:
            image_data_list = await self._download_images(image_attachments)
        except Exception as e:
            logger.error(f"Error downloading images: {str(e)}")
            await interaction.followup.send(
                f"❌ Error downloading images: {str(e)}",
                ephemeral=True
            )
            return

        # Process images with OCR
        try:
            await interaction.followup.send(
                f"🔍 Processing {len(image_data_list)} image(s) with OCR...\n"
                f"Type: **{ocr_type}**\n"
                f"This may take a moment..."
            )

            results = await self._ocr_service.process_images(image_data_list, ocr_type)
            
            # Save to database
            db = get_db()
            async with db.session() as session:
                await self._save_ocr_results(
                    session=session,
                    user_id=interaction.user.id,
                    username=interaction.user.name,
                    discriminator=interaction.user.discriminator,
                    guild_id=interaction.guild.id if interaction.guild else None,
                    channel_id=interaction.channel.id if interaction.channel else None,
                    ocr_type=ocr_type,
                    results=results
                )

            # Format and send results
            await self._send_results(interaction, ocr_type, results)

        except ValueError as e:
            logger.error(f"Invalid OCR type: {str(e)}")
            await interaction.followup.send(
                f"❌ {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error processing OCR: {str(e)}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred while processing the images: {str(e)}",
                ephemeral=True
            )

    async def _download_images(self, attachments: List[discord.Attachment]) -> List[bytes]:
        """
        Download all image attachments.

        Args:
            attachments: List of Discord attachments

        Returns:
            List of image data in bytes
        """
        image_data_list = []
        
        for attachment in attachments:
            logger.info(f"Downloading image: {attachment.filename} ({attachment.size} bytes)")
            try:
                image_data = await attachment.read()
                image_data_list.append(image_data)
            except Exception as e:
                logger.error(f"Error downloading {attachment.filename}: {str(e)}")
                raise

        return image_data_list

    async def _save_ocr_results(
        self,
        session,
        user_id: int,
        username: str,
        discriminator: str,
        guild_id: int | None,
        channel_id: int | None,
        ocr_type: str,
        results: List[dict]
    ):
        """
        Save OCR results to database.

        Args:
            session: Database session
            user_id: Discord user ID
            username: Discord username
            discriminator: Discord discriminator
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            ocr_type: Type of OCR extraction
            results: List of OCR results
        """
        # Get or create user
        user = await DatabaseService.get_or_create_user(
            session=session,
            user_id=user_id,
            username=username,
            discriminator=discriminator
        )

        # Determine overall success
        all_success = all(r.get('success', False) for r in results)
        error_messages = [r.get('error') for r in results if not r.get('success', False)]
        error_message = '; '.join(filter(None, error_messages)) if error_messages else None

        # Create OCR request record
        ocr_request = OCRRequest(
            user_id=user.id,
            guild_id=guild_id,
            channel_id=channel_id,
            ocr_type=ocr_type,
            image_count=len(results),
            success=all_success,
            error_message=error_message
        )
        session.add(ocr_request)
        await session.flush()  # Get the ID

        # Create OCR result records
        for result in results:
            ocr_result = OCRResult(
                ocr_request_id=ocr_request.id,
                image_index=result.get('image_index', 0),
                extracted_data=result.get('extracted_data'),
                raw_text=result.get('raw_text'),
                confidence_score=result.get('confidence_score'),
                success=result.get('success', False),
                error_message=result.get('error')
            )
            session.add(ocr_result)

        await session.commit()
        logger.info(f"Saved OCR request {ocr_request.id} with {len(results)} results to database")

    async def _send_results(
        self,
        interaction: discord.Interaction,
        ocr_type: str,
        results: List[dict]
    ):
        """
        Format and send OCR results to the user.

        Args:
            interaction: Discord interaction
            ocr_type: Type of OCR extraction
            results: List of OCR results
        """
        successful_results = [r for r in results if r.get('success', False)]
        failed_results = [r for r in results if not r.get('success', False)]

        # Create summary message
        summary = f"## 📊 OCR Results - {ocr_type.replace('-', ' ').title()}\n\n"
        summary += f"**Images processed:** {len(results)}\n"
        summary += f"**Successful:** {len(successful_results)} ✅\n"
        if failed_results:
            summary += f"**Failed:** {len(failed_results)} ❌\n\n"

        # Send results
        if successful_results:
            for result in successful_results:
                logger.info(f"Creating embed for result: {result}")
                embed = await self._create_result_embed(ocr_type, result)
                await interaction.followup.send(embed=embed)

        if failed_results:
            error_msg = "**Failed images:**\n"
            for result in failed_results:
                error_msg += f"• Image {result.get('image_index', 0) + 1}: {result.get('error', 'Unknown error')}\n"
            await interaction.followup.send(error_msg)

        # Send summary at the end
        await interaction.followup.send(summary)

    async def _create_result_embed(
        self,
        ocr_type: str,
        result: dict
    ) -> discord.Embed:
        """
        Create a Discord embed for OCR result.

        Args:
            ocr_type: Type of OCR extraction
            result: OCR result data

        Returns:
            Discord embed
        """
        extracted_data = result.get('extracted_data', {})
        confidence = result.get('confidence_score', 0.0)
        image_index = result.get('image_index', 0)

        embed = discord.Embed(
            title=f"Image {image_index + 1} - {ocr_type.replace('-', ' ').title()}",
            color=discord.Color.green()
        )

        # Add confidence score
        confidence_emoji = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
        embed.add_field(
            name="Confidence Score",
            value=f"{confidence_emoji} {confidence:.1%}",
            inline=False
        )

        # Format data based on OCR type
        if ocr_type == "alliance-ranking":
            self._format_alliance_ranking(embed, extracted_data)
        elif ocr_type == "kingdom-power-ranking":
            self._format_kingdom_ranking(embed, extracted_data)
        elif ocr_type == "kvk-points":
            self._format_kvk_points(embed, extracted_data)
        elif ocr_type == "alliance-members":
            self._format_alliance_members(embed, extracted_data)

        return embed

    def _format_alliance_ranking(self, embed: discord.Embed, data: dict):
        """Format alliance ranking data for embed."""
        if data.get('title'):
            embed.add_field(name="Title", value=data['title'], inline=False)
        if data.get('phase'):
            embed.add_field(name="Phase", value=data['phase'], inline=True)

        rankings = data.get('rankings', [])[:10]  # Limit to top 10
        if rankings:
            ranking_text = ""
            for entry in rankings:
                placement = entry.get('placement', '?')
                name = entry.get('name', 'Unknown')
                points = entry.get('points_contributed', 0)
                
                # Handle both string and int formats
                if isinstance(points, str):
                    points_display = points
                else:
                    points_display = f"{points:,}" if isinstance(points, int) else str(points)
                
                ranking_text += f"**#{placement}** - {name}: {points_display} points\n"
            
            embed.add_field(name="Rankings", value=ranking_text or "No data", inline=False)

    def _format_kingdom_ranking(self, embed: discord.Embed, data: dict):
        """Format kingdom power ranking data for embed."""
        if data.get('kingdom'):
            embed.add_field(name="Kingdom", value=data['kingdom'], inline=True)

        rankings = data.get('rankings', [])[:10]  # Limit to top 10
        if rankings:
            ranking_text = ""
            for entry in rankings:
                rank = entry.get('rank', '?')
                governor = entry.get('governor', 'Unknown')
                power = entry.get('power', '0')
                ranking_text += f"**#{rank}** - {governor}: {power}\n"
            
            embed.add_field(name="Rankings", value=ranking_text or "No data", inline=False)

    def _format_kvk_points(self, embed: discord.Embed, data: dict):
        """Format KVK points data for embed."""
        if data.get('phase'):
            embed.add_field(name="Phase", value=data['phase'], inline=True)
        if data.get('timestamp'):
            embed.add_field(name="Time", value=data['timestamp'], inline=True)

        player_points = data.get('player_points', [])[:10]  # Limit to top 10
        if player_points:
            points_text = ""
            for entry in player_points:
                rank = entry.get('rank', '?')
                name = entry.get('player_name', 'Unknown')
                points = entry.get('points', 0)
                kills = entry.get('kills', 0)
                deaths = entry.get('deaths', 0)
                
                # Handle string or int formats
                points_display = f"{points:,}" if isinstance(points, int) else str(points)
                kills_display = f"{kills:,}" if isinstance(kills, int) else str(kills)
                deaths_display = f"{deaths:,}" if isinstance(deaths, int) else str(deaths)
                
                points_text += f"**#{rank}** - {name}\n"
                points_text += f"  Points: {points_display} | K: {kills_display} | D: {deaths_display}\n"
            
            embed.add_field(name="Player Points", value=points_text or "No data", inline=False)

    def _format_alliance_members(self, embed: discord.Embed, data: dict):
        """Format alliance members data for embed."""
        if data.get('alliance_name'):
            embed.add_field(name="Alliance", value=data['alliance_name'], inline=True)
        if data.get('alliance_tag'):
            embed.add_field(name="Tag", value=data['alliance_tag'], inline=True)
        if data.get('total_power'):
            embed.add_field(name="Total Power", value=data['total_power'], inline=True)

        members = data.get('members', [])[:15]  # Limit to 15 members
        if members:
            member_text = ""
            for member in members:
                name = member.get('name', 'Unknown')
                power = member.get('power', '0')
                rank = member.get('rank', '')
                member_text += f"• {name} - {power}"
                if rank:
                    member_text += f" ({rank})"
                member_text += "\n"
            
            embed.add_field(name=f"Members ({len(members)})", value=member_text or "No data", inline=False)
