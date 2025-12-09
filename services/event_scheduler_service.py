"""Event Scheduler Service - Single Responsibility Principle."""

from datetime import datetime, timezone
from typing import List, Tuple, Dict, Optional
from abc import ABC, abstractmethod
import discord


class IEventSchedulerService(ABC):
    """Interface for event scheduling - Interface Segregation Principle."""

    @abstractmethod
    def schedule_event(
        self, channel_id: int, event_time: datetime, role_names: List[str], message: str
    ) -> bool:
        """Schedule a new event."""
        pass

    @abstractmethod
    def get_events_for_channel(
        self, channel_id: int
    ) -> List[Tuple[datetime, List[str], str]]:
        """Get all events for a specific channel."""
        pass

    @abstractmethod
    def check_and_get_due_events(
        self,
    ) -> Dict[int, List[Tuple[datetime, List[str], str]]]:
        """Check and return events that are due."""
        pass


class EventSchedulerService(IEventSchedulerService):
    """Service responsible for scheduling and managing timed events."""

    def __init__(self):
        """Initialize the event scheduler."""
        self._scheduled_events: Dict[int, List[Tuple[datetime, List[str], str]]] = {}

    def schedule_event(
        self, channel_id: int, event_time: datetime, role_names: List[str], message: str
    ) -> bool:
        """
        Schedule a new event.

        Args:
            channel_id: Discord channel ID
            event_time: When to trigger the event (UTC)
            role_names: List of role names to ping
            message: Message to send with the ping

        Returns:
            True if scheduled successfully
        """
        if event_time <= datetime.now(timezone.utc):
            return False

        if channel_id not in self._scheduled_events:
            self._scheduled_events[channel_id] = []

        self._scheduled_events[channel_id].append((event_time, role_names, message))
        # Sort events by time
        self._scheduled_events[channel_id].sort(key=lambda x: x[0])
        return True

    def get_events_for_channel(
        self, channel_id: int
    ) -> List[Tuple[datetime, List[str], str]]:
        """
        Get all scheduled events for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            List of events (event_time, role_names, message)
        """
        return self._scheduled_events.get(channel_id, []).copy()

    def check_and_get_due_events(
        self,
    ) -> Dict[int, List[Tuple[datetime, List[str], str]]]:
        """
        Check for events that are due and remove them from schedule.

        Returns:
            Dictionary mapping channel_id to list of due events
        """
        current_time = datetime.now(timezone.utc)
        due_events: Dict[int, List[Tuple[datetime, List[str], str]]] = {}

        for channel_id, events in list(self._scheduled_events.items()):
            channel_due_events = []

            for event in events[:]:
                event_time, role_names, message = event
                if current_time >= event_time:
                    channel_due_events.append(event)
                    self._scheduled_events[channel_id].remove(event)

            if channel_due_events:
                due_events[channel_id] = channel_due_events

            # Clean up empty channels
            if not self._scheduled_events[channel_id]:
                del self._scheduled_events[channel_id]

        return due_events

    def cancel_event(self, channel_id: int, index: int) -> bool:
        """
        Cancel a scheduled event by index.

        Args:
            channel_id: Discord channel ID
            index: Index of the event in the channel's event list

        Returns:
            True if cancelled successfully
        """
        if channel_id in self._scheduled_events:
            events = self._scheduled_events[channel_id]
            if 0 <= index < len(events):
                events.pop(index)
                if not events:
                    del self._scheduled_events[channel_id]
                return True
        return False
