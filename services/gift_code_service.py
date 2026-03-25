import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import GiftCodeRedemption
from services.kingshot_api import KingshotAPIClient

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

    def __init__(self):
        """
        Initialize gift code service.
        """
        self._client: Optional[KingshotAPIClient] = None
        logger.info("GiftCodeService initialized using original Kingshot API")

    async def __aenter__(self):
        """Enter async context manager - initialize shared client."""
        client = KingshotAPIClient()
        self._client = client
        await client.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - cleanup client."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def ensure_client(self) -> KingshotAPIClient:
        """Ensure client is initialized. Called if service is used without context manager."""
        if self._client is None:
            self._client = KingshotAPIClient()
        return self._client

    async def close(self) -> None:
        """Manually close the client if not using context manager."""
        if self._client is not None:
            await self._client.close()
            self._client = None

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
            # Ensure client is available
            api_client = await self.ensure_client()

            # The API requires an active session with cookies from the get_player call
            # Otherwise we'll receive a 'NOT LOGIN' error during redemption
            player_resp = await api_client.get_player(str(player_id))
            if player_resp.get("code") != 0:
                logger.warning(f"Failed to get_player before redeeming for {player_id}: {player_resp}")

            response_data = await api_client.redeem_code(str(player_id), gift_code)

            code = response_data.get("code")
            msg = response_data.get("msg", "Unknown error occurred")

            if code == 0:
                logger.info(f"Successfully redeemed gift code '{gift_code}' for player {player_id}")
                return {
                    "success": True,
                    "message": msg,
                    "data": response_data.get("data"),
                }
            else:
                err_code = str(response_data.get("err_code", ""))

                # Check if the error indicates the code was already redeemed
                already_redeemed_phrases = [
                    "already redeemed",
                    "already been redeemed",
                    "already used",
                    "already claimed",
                    "exceeded the limit",
                    "have already received",
                    "collected",
                    "same type exchange",
                    "time error",
                    "received.",
                ]
                is_already_redeemed = any(phrase in msg.lower() for phrase in already_redeemed_phrases)

                if is_already_redeemed:
                    logger.info(
                        f"Gift code '{gift_code}' was already redeemed for player {player_id} "
                        f"(detected from API response)"
                    )
                    return {
                        "success": False,  # Log as failed
                        "message": msg,
                        "error_code": "ALREADY_REDEEMED_BY_API",  # Special code to identify and skip next time
                        "error_details": {"err_code": err_code},
                        "already_redeemed_by_api": True,
                    }

                logger.warning(
                    f"Failed to redeem gift code '{gift_code}' for player {player_id}: " f"{msg} (code: {err_code})"
                )

                return {
                    "success": False,
                    "message": msg,
                    "error_code": err_code,
                    "error_details": {"err_code": err_code},
                }

        except ValueError as e:
            logger.error(
                f"Validation/Parse error redeeming gift code '{gift_code}' for player {player_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": "Error communicating with the API.",
                "error_code": "API_ERROR",
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
        Get available gift codes from kingshot.net API.

        Returns:
            Dictionary containing the API response with status and giftcodes
        """
        url = "https://kingshot.net/api/gift-codes"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch gift codes from kingshot.net, status: {response.status}")
                        return {
                            "success": False,
                            "message": f"HTTP Error {response.status}",
                        }

                    data = await response.json()

                    if data.get("status") != "success":
                        logger.error(f"kingshot.net API returned non-success status: {data.get('status')}")
                        return {
                            "success": False,
                            "message": data.get("message", "API Error"),
                        }

                    codes = data.get("data", {}).get("giftCodes", [])
                    logger.info(f"Successfully fetched {len(codes)} gift codes from kingshot.net")

                    return {
                        "success": True,
                        "data": codes,
                    }

        except asyncio.TimeoutError:
            logger.error("Timeout fetching gift codes from kingshot.net")
            return {
                "success": False,
                "message": "Request timed out",
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching gift codes from kingshot.net: {e}", exc_info=True)
            return {
                "success": False,
                "message": "An unexpected error occurred",
            }
