"""
Low-level Binance Futures Testnet REST client.

Handles:
- Request signing (HMAC-SHA256)
- Timestamping
- HTTP transport via requests
- Structured error handling and logging
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger(__name__)

# ── Testnet base URL ──────────────────────────────────────────────────────────
TESTNET_BASE_URL = "https://demo-fapi.binance.com"

# Default timeouts (connect, read) in seconds
DEFAULT_TIMEOUT = (5, 15)


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or error payload."""

    def __init__(self, status_code: int, code: int, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised on connection / timeout failures."""


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Parameters
    ----------
    api_key:    Testnet API key.
    api_secret: Testnet API secret.
    base_url:   Override the default testnet URL (useful for unit tests).
    timeout:    (connect_timeout, read_timeout) in seconds.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: tuple = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret must be non-empty strings.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceClient initialised → base_url=%s", self._base_url)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append HMAC-SHA256 signature and timestamp to params dict."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request and return the parsed JSON response.

        Args:
            method:   HTTP verb ('GET', 'POST', 'DELETE').
            endpoint: API path, e.g. '/fapi/v1/order'.
            params:   Query / body parameters.
            signed:   Whether to attach HMAC signature.

        Returns:
            Parsed JSON dict from the API.

        Raises:
            BinanceAPIError:     Non-2xx or error body from Binance.
            BinanceNetworkError: Connection / timeout failure.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{endpoint}"

        logger.debug(
            "→ %s %s  params=%s",
            method.upper(),
            url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=params, timeout=self._timeout
                )
            else:
                response = self._session.request(
                    method, url, data=params, timeout=self._timeout
                )
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s — %s", method, url, exc)
            raise BinanceNetworkError(f"Request timed out: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s %s — %s", method, url, exc)
            raise BinanceNetworkError(f"Connection error: {exc}") from exc

        logger.debug(
            "← HTTP %s  body=%s", response.status_code, response.text[:500]
        )

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text[:300])
            raise BinanceAPIError(
                response.status_code,
                -1,
                f"Non-JSON response: {response.text[:200]}",
            )

        if not response.ok or (isinstance(data, dict) and "code" in data and data["code"] < 0):
            code = data.get("code", -1) if isinstance(data, dict) else -1
            msg = data.get("msg", response.text) if isinstance(data, dict) else response.text
            logger.error(
                "API error HTTP %s code=%s msg=%s", response.status_code, code, msg
            )
            raise BinanceAPIError(response.status_code, code, msg)

        return data

    # ── Public methods ────────────────────────────────────────────────────────

    def get_server_time(self) -> Dict[str, Any]:
        """Ping Binance server and return server time."""
        return self._request("GET", "/fapi/v1/time")

    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Return exchange / symbol info."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)

    def get_account(self) -> Dict[str, Any]:
        """Return account information (signed)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures Testnet.

        Args:
            order_params: Dict of order fields as required by the API
                          (symbol, side, type, quantity, etc.).

        Returns:
            API response dict.
        """
        logger.info("Placing order → %s", order_params)
        result = self._request(
            "POST", "/fapi/v1/order", params=dict(order_params), signed=True
        )
        logger.info("Order response ← %s", result)
        return result

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by ID."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order → symbol=%s orderId=%s", symbol, order_id)
        result = self._request("DELETE", "/fapi/v1/order", params=params, signed=True)
        logger.info("Cancel response ← %s", result)
        return result

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query a single order by ID."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)
