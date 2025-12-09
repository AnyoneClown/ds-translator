"""Event Scheduling Command Handler - Single Responsibility Principle."""

import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
from typing import List
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

        @self._bot.command(name="schedule")
        async def schedule_event(ctx, date: str, time: str, *, message: str):
            """Schedule an @everyone ping 10 minutes before the specified time. Format: !schedule YYYY-MM-DD HH:MM Your message"""
            await self._handle_schedule_event(ctx, date, time, message)

        @self._bot.command(name="events")
        async def list_events(ctx):
            """List all scheduled events for this channel."""
            await self._handle_list_events(ctx)

        @self._bot.command(name="cancel")
        async def cancel_event(ctx, event_number: int):
            """Cancel a scheduled event. Use !events to see event numbers."""
            await self._handle_cancel_event(ctx, event_number)

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

    async def _handle_schedule_event(self, ctx, date: str, time: str, message: str):
        """Handle scheduling a new event."""
        try:
            from datetime import timedelta

            datetime_str = f"{date} {time}"
            event_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc
            )

            if event_time <= datetime.now(timezone.utc):
                await ctx.reply("You cannot schedule an event in the past!")
                return

            notification_time = event_time - timedelta(minutes=10)

            if notification_time <= datetime.now(timezone.utc):
                await ctx.reply(
                    "The event is too soon! Must be more than 10 minutes in the future."
                )
                return

            success = self._scheduler_service.schedule_event(
                ctx.channel.id, notification_time, ["everyone"], message
            )

            if success:
                await ctx.reply(
                    f"Scheduled @everyone ping for **{notification_time.strftime('%Y-%m-%d %H:%M')} UTC**\n"
                    f"(10 minutes before {event_time.strftime('%H:%M')})\n"
                    f"Message: {message}",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            else:
                await ctx.reply("Failed to schedule event.")
        except ValueError:
            await ctx.reply(
                "Invalid date/time format. Use: `!schedule YYYY-MM-DD HH:MM Your message`"
            )
        except Exception as e:
            print(f"Error scheduling event: {e}")
            await ctx.reply("An error occurred while scheduling the event.")

    async def _handle_list_events(self, ctx):
        """Handle listing all scheduled events for a channel."""
        events = self._scheduler_service.get_events_for_channel(ctx.channel.id)

        if not events:
            await ctx.reply("No scheduled events in this channel.")
            return

        events_list = []
        for idx, (event_time, role_names, message) in enumerate(events, 1):
            events_list.append(
                f"**{idx}.** {event_time.strftime('%Y-%m-%d %H:%M')} UTC\n"
                f"   {message}"
            )

        await ctx.reply(
            "**Scheduled Events:**\n\n" + "\n\n".join(events_list),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _handle_cancel_event(self, ctx, event_number: int):
        """Handle cancelling a scheduled event."""
        try:
            index = event_number - 1

            if self._scheduler_service.cancel_event(ctx.channel.id, index):
                await ctx.reply(f"Cancelled event #{event_number}")
            else:
                await ctx.reply(
                    f"Event #{event_number} not found. Use `!events` to see available events."
                )
        except Exception as e:
            print(f"Error cancelling event: {e}")
            await ctx.reply("An error occurred while cancelling the event.")

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

    async def _send_event_notification(
        self, channel: discord.TextChannel, role_names: List[str], message: str
    ):
        """Send event notification with @everyone ping."""
        notification = f"@everyone\n{message}"
        await channel.send(notification)
