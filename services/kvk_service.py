import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class IKVKService(ABC):
    """Interface for KVK (Kingdom vs Kingdom) service."""

    @abstractmethod
    async def get_kvk_matches(self, kingdom_number: int) -> Dict[str, Any]:
        """Get KVK matches for a specific kingdom."""
        pass


class KVKService(IKVKService):
    """Service responsible for fetching KVK matches via external API."""

    def __init__(self, api_base_url: str = "https://kingshot.net/api"):
        """
        Initialize KVK service.

        Args:
            api_base_url: Base URL for the KVK API
        """
        self._api_base_url = api_base_url
        self._endpoint = f"{api_base_url}/kvk/matches"
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"KVKService initialized with endpoint: {self._endpoint}")

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

    async def get_kvk_matches(self, kingdom_number: int) -> Dict[str, Any]:
        """
        Get KVK matches for a specific kingdom.

        Args:
            kingdom_number: The kingdom number to fetch matches for

        Returns:
            Dictionary containing the API response with KVK matches
        """
        logger.info(f"Fetching KVK matches for kingdom {kingdom_number} from {self._endpoint}")

        try:
            # Ensure session is available
            http_session = await self.ensure_session()
            params = {"kingdom_a": kingdom_number}

            async with http_session.get(
                self._endpoint,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response_data = await response.json()

                if response.status == 200 and response_data.get("status") == "success":
                    data = response_data.get("data", [])
                    logger.info(f"Successfully fetched {len(data)} KVK matches for kingdom {kingdom_number}")
                    return {
                        "success": True,
                        "data": data,
                        "pagination": response_data.get("pagination"),
                        "message": response_data.get("message", "Matches retrieved successfully"),
                        "timestamp": response_data.get("timestamp"),
                    }
                else:
                    error_message = response_data.get("message", "Failed to fetch KVK matches")
                    logger.warning(f"Failed to fetch KVK matches for kingdom {kingdom_number}: {error_message}")
                    return {
                        "success": False,
                        "message": error_message,
                        "status_code": response.status,
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching KVK matches for kingdom {kingdom_number}: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Network error occurred while fetching KVK matches.",
                "error_code": "NETWORK_ERROR",
            }
        except Exception as e:
            logger.error(
                f"Unexpected error fetching KVK matches for kingdom {kingdom_number}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": "An unexpected error occurred.",
                "error_code": "UNEXPECTED_ERROR",
            }
