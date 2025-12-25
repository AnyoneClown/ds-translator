import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

import aiohttp

logger = logging.getLogger(__name__)


class IGiftCodeService(ABC):
    """Interface for gift code service - Interface Segregation Principle."""

    @abstractmethod
    async def redeem_gift_code(self, player_id: int, gift_code: str) -> Dict[str, Any]:
        """Redeem a gift code for a player."""
        pass


class GiftCodeService(IGiftCodeService):
    """Service responsible for redeeming gift codes via external API."""

    def __init__(self, api_base_url: str = "https://kingshot.net/api"):
        """
        Initialize gift code service.

        Args:
            api_base_url: Base URL for the gift code API
        """
        self._api_base_url = api_base_url
        self._endpoint = f"{api_base_url}/gift-codes/redeem"
        logger.info(f"GiftCodeService initialized with endpoint: {self._endpoint}")

    async def redeem_gift_code(self, player_id: int, gift_code: str) -> Dict[str, Any]:
        """
        Redeem a gift code for a player.

        Args:
            player_id: The player ID to redeem the code for
            gift_code: The gift code to redeem

        Returns:
            Dictionary containing the API response with status, message, and data
        """
        logger.info(f"Redeeming gift code '{gift_code}' for player ID: {player_id}")

        payload = {"playerId": player_id, "giftCode": gift_code}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    response_data = await response.json()

                    if response.status == 200 and response_data.get("status") == "success":
                        logger.info(f"Successfully redeemed gift code '{gift_code}' for player {player_id}")
                        return {
                            "success": True,
                            "message": response_data.get("message", "Gift code redeemed successfully."),
                            "data": response_data.get("data"),
                            "timestamp": response_data.get("timestamp"),
                        }
                    else:
                        # Handle error responses
                        error_message = response_data.get("message", "Unknown error occurred")
                        error_code = None
                        error_details = None

                        if response_data.get("meta"):
                            meta = response_data["meta"]
                            error_code = meta.get("code")
                            error_details = meta.get("details", {}).get("code")

                        logger.warning(
                            f"Failed to redeem gift code '{gift_code}' for player {player_id}: "
                            f"{error_message} (code: {error_code})"
                        )

                        return {
                            "success": False,
                            "message": error_message,
                            "error_code": error_code,
                            "error_details": error_details,
                            "timestamp": response_data.get("timestamp"),
                        }

        except aiohttp.ClientError as e:
            logger.error(
                f"Network error redeeming gift code '{gift_code}' for player {player_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": "Network error occurred while redeeming gift code.",
                "error_code": "NETWORK_ERROR",
            }
        except Exception as e:
            logger.error(
                f"Unexpected error redeeming gift code '{gift_code}' for player {player_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": "An unexpected error occurred.",
                "error_code": "UNEXPECTED_ERROR",
            }
