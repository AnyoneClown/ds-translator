import hashlib
import time
import urllib.parse
from typing import Any, Dict, Optional

import aiohttp

SALT = "mN4!pQs6JrYwV9"
HOSTNAME = "https://kingshot-giftcode.centurygame.com"


class KingshotAPIClient:
    """Client for original Kingshot gift code and player API."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is initialized."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Manually close the session."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    def _sign(self, params: Dict[str, str]) -> str:
        """Sign parameters using MD5 and SALT."""
        sorted_keys = sorted(params.keys())
        query_string = "&".join(f"{k}={params[k]}" for k in sorted_keys)
        string_to_sign = query_string + SALT
        return hashlib.md5(string_to_sign.encode("utf-8")).hexdigest()

    async def _request(self, path: str, params: Dict[str, str]) -> Dict[str, Any]:
        """Make a signed POST request to the API."""
        params_with_sign = params.copy()
        params_with_sign["sign"] = self._sign(params)

        body = urllib.parse.urlencode(params_with_sign)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(body)),
        }

        url = f"{HOSTNAME}/api{path}"
        session = await self.ensure_session()

        try:
            async with session.post(
                url, data=body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                try:
                    # E.g. {'code': 1, 'msg': 'role not exist.', 'data': [], 'err_code': 40004}
                    return await response.json()
                except Exception as e:
                    text = await response.text()
                    raise ValueError(f"Failed to parse JSON response: {text}") from e
        except Exception as e:
            raise ValueError(f"HTTP request failed: {e}") from e

    async def get_player(self, player_id: str) -> Dict[str, Any]:
        """Fetch player information."""
        timestamp = str(int(time.time() * 1000))
        params = {"fid": str(player_id), "time": timestamp}
        return await self._request("/player", params)

    async def redeem_code(self, player_id: str, gift_code: str, captcha_code: str = "") -> Dict[str, Any]:
        """Redeem a gift code."""
        timestamp = str(int(time.time() * 1000))
        params = {
            "fid": str(player_id),
            "cdk": gift_code,
            "captcha_code": captcha_code,
            "time": timestamp,
        }
        return await self._request("/gift_code", params)
