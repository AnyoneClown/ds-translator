from datetime import datetime, timezone
from typing import List

import discord
from discord import app_commands
from discord.ext import commands, tasks

from services.event_scheduler_service import IEventSchedulerService


class EventHandler:
    """Handles event scheduling Discord commands."""

    def __init__(self, scheduler_service: IEventSchedulerService, bot: commands.Bot):
        """
        Initialize event handler.

            scheduler_service: Service for managing scheduled events
            bot: Discord bot instance
        """
        self._scheduler_service = scheduler_service
        self._bot = bot

    def register_commands(self):
        """Register all event scheduling commands with the bot."""

        @self._bot.tree.command(
            name="schedule", description="Schedule an @everyone ping 10 minutes before the specified time"
        )
        @app_commands.describe(
            date="Event date (YYYY-MM-DD)", time="Event time (HH:MM in UTC)", message="Event message"
        )
        async def schedule_event(interaction: discord.Interaction, date: str, time: str, message: str):
            """Schedule an @everyone ping 10 minutes before the specified time."""
            await self._handle_schedule_event(interaction, date, time, message)

        @self._bot.tree.command(name="events", description="List all scheduled events for this channel")
        async def list_events(interaction: discord.Interaction):
            """List all scheduled events for this channel."""
            await self._handle_list_events(interaction)

        @self._bot.tree.command(name="cancel", description="Cancel a scheduled event")
        @app_commands.describe(event_number="Event number from /events command")
        async def cancel_event(interaction: discord.Interaction, event_number: int):
            """Cancel a scheduled event. Use /events to see event numbers."""
            await self._handle_cancel_event(interaction, event_number)

    def start_scheduler_task(self):
        """Start the background task that checks for due events."""

        @tasks.loop(minutes=1)
        async def check_scheduled_events():
            """Check for scheduled events and ping roles when it's time."""
            due_events = self._scheduler_service.check_and_get_due_events()

            for channel_id, events in due_events.items():
                channel = self._bot.get_channel(channel_id)
                if not channel:
                    continue

                for event_time, role_names, message in events:
                    await self._send_event_notification(channel, role_names, message)

        check_scheduled_events.start()

    async def _handle_schedule_event(self, interaction: discord.Interaction, date: str, time: str, message: str):
        """Handle scheduling a new event."""
        await interaction.response.defer(thinking=True)

        try:
            from datetime import timedelta

            datetime_str = f"{date} {time}"
            event_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

            if event_time <= datetime.now(timezone.utc):
                await interaction.followup.send("You cannot schedule an event in the past!")
                return

            notification_time = event_time - timedelta(minutes=10)

            if notification_time <= datetime.now(timezone.utc):
                await interaction.followup.send("The event is too soon! Must be more than 10 minutes in the future.")
                return

            success = self._scheduler_service.schedule_event(
                interaction.channel.id, notification_time, ["everyone"], message
            )

            if success:
                await interaction.followup.send(
                    f"Scheduled @everyone ping for **{notification_time.strftime('%Y-%m-%d %H:%M')} UTC**\n"
                    f"(10 minutes before {event_time.strftime('%H:%M')})\n"
                    f"Message: {message}",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            else:
                await interaction.followup.send("Failed to schedule event.")
        except ValueError:
            await interaction.followup.send("Invalid date/time format. Use: YYYY-MM-DD for date and HH:MM for time")
        except Exception as e:
            print(f"Error scheduling event: {e}")
            await interaction.followup.send("An error occurred while scheduling the event.")

    async def _handle_list_events(self, interaction: discord.Interaction):
        """Handle listing all scheduled events for a channel."""
        await interaction.response.defer(thinking=True)

        events = self._scheduler_service.get_events_for_channel(interaction.channel.id)

        if not events:
            await interaction.followup.send("No scheduled events in this channel.")
            return

        events_list = []
        for idx, (event_time, role_names, message) in enumerate(events, 1):
            events_list.append(f"**{idx}.** {event_time.strftime('%Y-%m-%d %H:%M')} UTC\n" f"   {message}")

        await interaction.followup.send(
            "**Scheduled Events:**\n\n" + "\n\n".join(events_list),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _handle_cancel_event(self, interaction: discord.Interaction, event_number: int):
        """Handle cancelling a scheduled event."""
        await interaction.response.defer(thinking=True)

        try:
            index = event_number - 1

            if self._scheduler_service.cancel_event(interaction.channel.id, index):
                await interaction.followup.send(f"Cancelled event #{event_number}")
            else:
                await interaction.followup.send(
                    f"Event #{event_number} not found. Use `/events` to see available events."
                )
        except Exception as e:
            print(f"Error cancelling event: {e}")
            await interaction.followup.send("An error occurred while cancelling the event.")

    async def _extract_role_names(self, guild: discord.Guild, args: tuple) -> List[str]:
        """Extract role names from command arguments (supports both @mentions and plain text)."""
        role_names = []
        for arg in args:
            if arg.startswith("<@&"):
                role_id = arg.strip("<@&>")
                role = discord.utils.get(guild.roles, id=int(role_id))
                if role:
                    role_names.append(role.name)
            else:
                role = discord.utils.get(guild.roles, name=arg)
                if role:
                    role_names.append(arg)
                    break
        return role_names

    def _extract_message(self, args: tuple) -> str:
        """Extract message text from command arguments."""
        message_parts = []
        found_role = False
        for arg in args:
            if not found_role and not arg.startswith("<@&"):
                found_role = True
                continue
            if found_role and not arg.startswith("<@&"):
                message_parts.append(arg)
        return " ".join(message_parts) if message_parts else "Event reminder!"

    async def _send_event_notification(self, channel: discord.TextChannel, role_names: List[str], message: str):
        """Send event notification with @everyone ping."""
        notification = f"@everyone\n{message}"
        await channel.send(notification)
