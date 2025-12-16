from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import aiohttp


class IPlayerInfoService(ABC):
    """Interface for player info service - Interface Segregation Principle."""

    @abstractmethod
    async def get_player_info(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Fetch player information by ID."""
        pass


class PlayerInfoService(IPlayerInfoService):
    """Service responsible for fetching player information from external API."""

    def __init__(self, api_base_url: str = "https://kingshot.net/api"):
        """
        Initialize player info service.

        Args:
            api_base_url: Base URL for the player info API
        """
        self._api_base_url = api_base_url
        self._endpoint = f"{api_base_url}/player-info"

    async def get_player_info(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch player information from the API.

        Args:
            player_id: The player ID to look up

        Returns:
            Dictionary containing player information, or None if request failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self._endpoint, params={"playerId": player_id}, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        response = await response.json()
                        return response.get("data")
                    elif response.status == 404:
                        return None
                    else:
                        print(f"API error: Status {response.status}")
                        return None
        except aiohttp.ClientError as e:
            print(f"Network error fetching player info: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching player info: {e}")
            return None

    def format_player_stats(self, player_data: Dict[str, Any]) -> str:
        """
        Format player data into a readable string.

        Args:
            player_data: Raw player data from API

        Returns:
            Formatted string with player statistics
        """
        if not player_data:
            return "No data available"

        # Format with emojis
        lines = []
        
        # Name
        if "name" in player_data:
            lines.append(f"👤 **Name:** {player_data['name']}")
        
        # Player ID
        if "playerId" in player_data:
            lines.append(f"🆔 **ID:** {player_data['playerId']}")
        
        # Castle Level
        if "levelRendered" in player_data:
            level_info = player_data['levelRendered']
            if "levelRenderedDetailed" in player_data:
                level_info = player_data['levelRenderedDetailed']
            lines.append(f"🏰 **Castle Level:** {level_info}")
        elif "level" in player_data:
            lines.append(f"🏰 **Castle Level:** Level {player_data['level']}")
        
        # Kingdom
        if "kingdom" in player_data:
            lines.append(f"🌍 **Kingdom:** {player_data['kingdom']}")

        return "\n".join(lines)
