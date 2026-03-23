"""
Order placement logic — sits between the CLI layer and the raw API client.

Responsibilities:
- Build properly shaped order payloads for each order type.
- Invoke the client and return a normalised OrderResult.
- Provide a human-readable summary / pretty-print helper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import get_logger

logger = get_logger(__name__)


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class OrderResult:
    """Normalised representation of a Binance order response."""

    success: bool
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    price: Optional[str] = None
    avg_price: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    time_in_force: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "OrderResult":
        return cls(
            success=True,
            order_id=data.get("orderId"),
            client_order_id=data.get("clientOrderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            price=data.get("price"),
            avg_price=data.get("avgPrice"),
            orig_qty=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            time_in_force=data.get("timeInForce"),
            raw=data,
        )

    @classmethod
    def from_error(cls, message: str) -> "OrderResult":
        return cls(success=False, error_message=message)


# ── Order builder helpers ─────────────────────────────────────────────────────


def _build_market_order(
    symbol: str, side: str, quantity: float
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
    }


def _build_limit_order(
    symbol: str, side: str, quantity: float, price: float
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": "GTC",
    }


def _build_stop_market_order(
    symbol: str, side: str, quantity: float, stop_price: float
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "side": side,
        "type": "STOP_MARKET",
        "quantity": quantity,
        "stopPrice": stop_price,
    }


# ── Main entry point ──────────────────────────────────────────────────────────


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> OrderResult:
    """
    Build the order payload and submit it through the client.

    Args:
        client:     Initialised BinanceClient.
        symbol:     Trading pair, e.g. 'BTCUSDT'.
        side:       'BUY' or 'SELL'.
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:   Order size.
        price:      Limit price (required for LIMIT orders).
        stop_price: Trigger price (required for STOP_MARKET orders).

    Returns:
        OrderResult with success flag and parsed fields.
    """
    order_type = order_type.upper()

    if order_type == "MARKET":
        payload = _build_market_order(symbol, side, quantity)
    elif order_type == "LIMIT":
        if price is None:
            return OrderResult.from_error("Price is required for LIMIT orders.")
        payload = _build_limit_order(symbol, side, quantity, price)
    elif order_type == "STOP_MARKET":
        if stop_price is None:
            return OrderResult.from_error(
                "Stop price is required for STOP_MARKET orders."
            )
        payload = _build_stop_market_order(symbol, side, quantity, stop_price)
    else:
        return OrderResult.from_error(f"Unsupported order type: '{order_type}'.")

    logger.info(
        "Submitting %s %s order | symbol=%s qty=%s price=%s stop=%s",
        side,
        order_type,
        symbol,
        quantity,
        price,
        stop_price,
    )

    try:
        response = client.place_order(payload)
        result = OrderResult.from_api_response(response)
        logger.info(
            "Order placed successfully | orderId=%s status=%s",
            result.order_id,
            result.status,
        )
        return result

    except BinanceAPIError as exc:
        logger.error("Binance API error while placing order: %s", exc)
        return OrderResult.from_error(str(exc))

    except BinanceNetworkError as exc:
        logger.error("Network error while placing order: %s", exc)
        return OrderResult.from_error(f"Network error: {exc}")

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while placing order: %s", exc)
        return OrderResult.from_error(f"Unexpected error: {exc}")


# ── Pretty-print helpers ──────────────────────────────────────────────────────

_SEP = "─" * 52


def print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
) -> None:
    """Print a formatted order request summary to stdout."""
    print(f"\n{'═' * 52}")
    print("  ORDER REQUEST SUMMARY")
    print(_SEP)
    print(f"  Symbol     : {symbol}")
    print(f"  Side       : {side}")
    print(f"  Type       : {order_type}")
    print(f"  Quantity   : {quantity}")
    if price is not None:
        print(f"  Price      : {price}")
    if stop_price is not None:
        print(f"  Stop Price : {stop_price}")
    print(f"{'═' * 52}\n")


def print_order_result(result: OrderResult) -> None:
    """Print a formatted order result to stdout."""
    if not result.success:
        print(f"\n{'═' * 52}")
        print("  ✗  ORDER FAILED")
        print(_SEP)
        print(f"  Error : {result.error_message}")
        print(f"{'═' * 52}\n")
        return

    print(f"\n{'═' * 52}")
    print("  ✓  ORDER PLACED SUCCESSFULLY")
    print(_SEP)
    print(f"  Order ID       : {result.order_id}")
    print(f"  Client Ord ID  : {result.client_order_id}")
    print(f"  Symbol         : {result.symbol}")
    print(f"  Side           : {result.side}")
    print(f"  Type           : {result.order_type}")
    print(f"  Status         : {result.status}")
    print(f"  Orig Qty       : {result.orig_qty}")
    print(f"  Executed Qty   : {result.executed_qty}")
    if result.price and result.price != "0":
        print(f"  Price          : {result.price}")
    if result.avg_price and result.avg_price != "0":
        print(f"  Avg Price      : {result.avg_price}")
    if result.time_in_force:
        print(f"  Time in Force  : {result.time_in_force}")
    print(f"{'═' * 52}\n")
