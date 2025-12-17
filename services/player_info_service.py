import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


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
        logger.info(f"PlayerInfoService initialized with endpoint: {self._endpoint}")

    async def get_player_info(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch player information from the API.

        Args:
            player_id: The player ID to look up

        Returns:
            Dictionary containing player information, or None if request failed
        """
        logger.info(f"Fetching player info for ID: {player_id}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self._endpoint,
                    params={"playerId": player_id},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        response = await response.json()
                        player_data = response.get("data")
                        if player_data:
                            logger.info(
                                f"Successfully fetched player info for ID {player_id}: "
                                f"{player_data.get('name', 'Unknown')} (Kingdom {player_data.get('kingdom', 'N/A')})"
                            )
                        else:
                            logger.warning(f"API returned 200 but no data for player ID: {player_id}")
                        return player_data
                    elif response.status == 404:
                        logger.warning(f"Player not found: {player_id}")
                        return None
                    else:
                        logger.error(f"API error for player {player_id}: Status {response.status}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(
                f"Network error fetching player info for {player_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching player info for {player_id}: {e}",
                exc_info=True,
            )
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
            level_info = player_data["levelRendered"]
            if "levelRenderedDetailed" in player_data:
                level_info = player_data["levelRenderedDetailed"]
            lines.append(f"🏰 **Castle Level:** {level_info}")
        elif "level" in player_data:
            lines.append(f"🏰 **Castle Level:** Level {player_data['level']}")

        # Kingdom
        if "kingdom" in player_data:
            lines.append(f"🌍 **Kingdom:** {player_data['kingdom']}")

        return "\n".join(lines)
