"""
Input validators for CLI arguments passed to the trading bot.
All validators raise ValueError with a human-readable message on failure.
"""

from __future__ import annotations

from typing import Optional

from bot.logging_config import get_logger

logger = get_logger(__name__)

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}

MIN_QUANTITY = 1e-8
MAX_QUANTITY = 1_000_000.0
MIN_PRICE = 1e-8
MAX_PRICE = 10_000_000.0


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol must not be empty.")
    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Use alphanumeric characters only (e.g. BTCUSDT)."
        )
    logger.debug("Symbol validated: %s", symbol)
    return symbol


def validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    logger.debug("Side validated: %s", side)
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    logger.debug("Order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity: float) -> float:
    if quantity <= 0:
        raise ValueError(f"Quantity must be positive, got {quantity}.")
    if quantity < MIN_QUANTITY:
        raise ValueError(f"Quantity {quantity} is below the minimum allowed ({MIN_QUANTITY}).")
    if quantity > MAX_QUANTITY:
        raise ValueError(f"Quantity {quantity} exceeds the maximum allowed ({MAX_QUANTITY}).")
    logger.debug("Quantity validated: %s", quantity)
    return quantity


def validate_price(price: Optional[float], order_type: str) -> Optional[float]:
    order_type = order_type.strip().upper()

    # MARKET and STOP_MARKET do NOT use --price
    if order_type in ("MARKET", "STOP_MARKET"):
        if price is not None:
            raise ValueError(
                f"Price must not be specified for {order_type} orders. Remove the --price flag."
            )
        logger.debug("Price not required for %s order.", order_type)
        return None

    # LIMIT requires a price
    if price is None:
        raise ValueError(f"Price is required for {order_type} orders. Provide it with --price.")
    if price <= 0:
        raise ValueError(f"Price must be positive, got {price}.")
    if price < MIN_PRICE:
        raise ValueError(f"Price {price} is below the minimum allowed ({MIN_PRICE}).")
    if price > MAX_PRICE:
        raise ValueError(f"Price {price} exceeds the maximum allowed ({MAX_PRICE}).")
    logger.debug("Price validated: %s", price)
    return price


def validate_stop_price(stop_price: Optional[float], order_type: str) -> Optional[float]:
    order_type = order_type.strip().upper()

    if order_type != "STOP_MARKET":
        if stop_price is not None:
            raise ValueError("Stop price is only applicable to STOP_MARKET orders.")
        return None

    if stop_price is None:
        raise ValueError("Stop price (--stop-price) is required for STOP_MARKET orders.")
    if stop_price <= 0:
        raise ValueError(f"Stop price must be positive, got {stop_price}.")
    logger.debug("Stop price validated: %s", stop_price)
    return stop_price


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> dict:
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type),
        "stop_price": validate_stop_price(stop_price, order_type),
    }
