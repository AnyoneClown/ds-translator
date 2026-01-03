import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import GiftCodeRedemption

logger = logging.getLogger(__name__)


class IGiftCodeService(ABC):
    """Interface for gift code service - Interface Segregation Principle."""

    @abstractmethod
    async def redeem_gift_code(self, session: AsyncSession, player_id: int, gift_code: str) -> Dict[str, Any]:
        """Redeem a gift code for a player."""
        pass

    @abstractmethod
    async def check_already_redeemed(
        self, session: AsyncSession, player_id: int, gift_code: str
    ) -> Optional[GiftCodeRedemption]:
        """Check if a gift code has already been successfully redeemed for a player."""
        pass

    @abstractmethod
    async def get_redeemed_players(self, session: AsyncSession, gift_code: str) -> set[str]:
        """Get set of player IDs who have already successfully redeemed this gift code."""
        pass

    @abstractmethod
    async def get_available_gift_codes(self) -> Dict[str, Any]:
        """Get available gift codes from the API."""
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
        self._list_endpoint = f"{api_base_url}/gift-codes"
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"GiftCodeService initialized with endpoint: {self._endpoint}")

    async def __aenter__(self):
        """Enter async context manager - initialize shared session."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - cleanup session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is initialized. Called if service is used without context manager."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Manually close the session if not using context manager."""
        if self._session:
            await self._session.close()
            self._session = None

    async def check_already_redeemed(
        self, session: AsyncSession, player_id: int, gift_code: str
    ) -> Optional[GiftCodeRedemption]:
        """
        Check if a gift code has already been successfully redeemed for a player.

        Args:
            session: Database session
            player_id: The player ID to check
            gift_code: The gift code to check

        Returns:
            GiftCodeRedemption object if already redeemed successfully, None otherwise
        """
        result = await session.execute(
            select(GiftCodeRedemption)
            .where(GiftCodeRedemption.player_id == str(player_id))
            .where(GiftCodeRedemption.gift_code == gift_code)
            .where(GiftCodeRedemption.success.is_(True))
            .order_by(GiftCodeRedemption.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_redeemed_players(self, session: AsyncSession, gift_code: str) -> set[str]:
        """
        Get set of player IDs who have already successfully redeemed this gift code.
        This includes both successful redemptions and failed attempts where the API
        indicated the code was already redeemed.
        This is more efficient than checking each player individually.

        Args:
            session: Database session
            gift_code: The gift code to check

        Returns:
            Set of player IDs (as strings) that have already redeemed this code
        """
        from sqlalchemy import or_

        # Get successful redemptions OR failed redemptions with already-redeemed indicators
        result = await session.execute(
            select(GiftCodeRedemption.player_id)
            .where(GiftCodeRedemption.gift_code == gift_code)
            .where(
                or_(
                    GiftCodeRedemption.success.is_(True),
                    GiftCodeRedemption.error_code == "ALREADY_REDEEMED_BY_API",
                )
            )
        )
        player_ids = result.scalars().all()
        return set(player_ids)

    async def redeem_gift_code(self, session: AsyncSession, player_id: int, gift_code: str) -> Dict[str, Any]:
        """
        Redeem a gift code for a player.

        Args:
            session: Database session
            player_id: The player ID to redeem the code for
            gift_code: The gift code to redeem

        Returns:
            Dictionary containing the API response with status, message, and data
        """
        # Check if already redeemed
        existing_redemption = await self.check_already_redeemed(session, player_id, gift_code)
        if existing_redemption:
            logger.info(
                f"Gift code '{gift_code}' already redeemed for player {player_id} at {existing_redemption.created_at}. "
                f"Skipping API call."
            )
            return {
                "success": False,
                "message": "This gift code has already been redeemed for this player.",
                "error_code": "ALREADY_REDEEMED",
                "already_redeemed": True,
                "redeemed_at": existing_redemption.created_at.isoformat(),
            }

        logger.info(f"Redeeming gift code '{gift_code}' for player ID: {player_id}")

        payload = {"playerId": player_id, "giftCode": gift_code}

        try:
            # Ensure session is available (supports both context manager and manual usage)
            http_session = await self.ensure_session()
            async with http_session.post(
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

                    # Check if the error indicates the code was already redeemed
                    already_redeemed_phrases = [
                        "already redeemed",
                        "already been redeemed",
                        "already used",
                        "already claimed",
                    ]
                    is_already_redeemed = any(phrase in error_message.lower() for phrase in already_redeemed_phrases)

                    if is_already_redeemed:
                        logger.info(
                            f"Gift code '{gift_code}' was already redeemed for player {player_id} "
                            f"(detected from API response)"
                        )
                        return {
                            "success": False,  # Log as failed
                            "message": error_message,
                            "error_code": "ALREADY_REDEEMED_BY_API",  # Special code to identify and skip next time
                            "error_details": error_details,
                            "timestamp": response_data.get("timestamp"),
                            "already_redeemed_by_api": True,
                        }

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

    async def get_available_gift_codes(self) -> Dict[str, Any]:
        """
        Get available gift codes from the API.

        Returns:
            Dictionary containing the API response with gift codes list
        """
        logger.info(f"Fetching available gift codes from {self._list_endpoint}")

        try:
            # Ensure session is available
            http_session = await self.ensure_session()
            async with http_session.get(
                self._list_endpoint,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response_data = await response.json()

                if response.status == 200 and response_data.get("status") == "success":
                    logger.info(
                        f"Successfully fetched gift codes: {response_data.get('data', {}).get('activeCount', 0)} active"
                    )
                    return {
                        "success": True,
                        "data": response_data.get("data"),
                        "message": response_data.get("message", "Gift codes retrieved successfully"),
                        "timestamp": response_data.get("timestamp"),
                    }
                else:
                    error_message = response_data.get("message", "Failed to fetch gift codes")
                    logger.warning(f"Failed to fetch gift codes: {error_message}")
                    return {
                        "success": False,
                        "message": error_message,
                        "status_code": response.status,
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching gift codes: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Network error occurred while fetching gift codes.",
                "error_code": "NETWORK_ERROR",
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching gift codes: {e}", exc_info=True)
            return {
                "success": False,
                "message": "An unexpected error occurred.",
                "error_code": "UNEXPECTED_ERROR",
            }
