#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI entry point.

Usage examples
--------------
# Market BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# Limit SELL
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 110000

# Stop-Market SELL (bonus order type)
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop-price 90000

Credentials are read from environment variables:
  BINANCE_API_KEY    — testnet API key
  BINANCE_API_SECRET — testnet API secret

Or pass them explicitly:
  --api-key  <key>
  --api-secret <secret>
"""

from __future__ import annotations

import argparse
import os
import sys

from bot.client import BinanceClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order, print_order_summary, print_order_result
from bot.validators import validate_all


# ── Bootstrap logging before anything else ───────────────────────────────────
setup_logging("DEBUG")
logger = get_logger(__name__)


# ── Argument parsing ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Credentials (optional — fall back to env vars) ────────────────────────
    creds = parser.add_argument_group("API credentials (override env vars)")
    creds.add_argument(
        "--api-key",
        metavar="KEY",
        help="Binance testnet API key (or set BINANCE_API_KEY env var)",
    )
    creds.add_argument(
        "--api-secret",
        metavar="SECRET",
        help="Binance testnet API secret (or set BINANCE_API_SECRET env var)",
    )

    # ── Order parameters ──────────────────────────────────────────────────────
    order = parser.add_argument_group("Order parameters")
    order.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    order.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        metavar="SIDE",
        help="Order side: BUY or SELL",
    )
    order.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"],
        metavar="TYPE",
        help="Order type: MARKET, LIMIT, or STOP_MARKET",
    )
    order.add_argument(
        "--qty",
        dest="quantity",
        required=True,
        type=float,
        metavar="QUANTITY",
        help="Order quantity (e.g. 0.001)",
    )
    order.add_argument(
        "--price",
        type=float,
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders)",
    )
    order.add_argument(
        "--stop-price",
        type=float,
        default=None,
        metavar="STOP_PRICE",
        help="Stop/trigger price (required for STOP_MARKET orders)",
    )

    # ── Misc ──────────────────────────────────────────────────────────────────
    parser.add_argument(
        "--log-level",
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging verbosity (default: DEBUG)",
    )

    return parser


# ── Credential resolution ─────────────────────────────────────────────────────


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """
    Return (api_key, api_secret) from CLI args → env vars.

    Raises SystemExit if either is missing.
    """
    api_key = args.api_key or os.environ.get("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET", "")

    missing = []
    if not api_key:
        missing.append("API key (--api-key or BINANCE_API_KEY)")
    if not api_secret:
        missing.append("API secret (--api-secret or BINANCE_API_SECRET)")

    if missing:
        print("\n✗  Missing credentials:")
        for m in missing:
            print(f"   • {m}")
        print()
        sys.exit(1)

    return api_key, api_secret


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Re-init logging with user-specified level
    setup_logging(args.log_level)
    logger.debug("CLI args: %s", vars(args))

    # ── Resolve credentials ────────────────────────────────────────────────────
    api_key, api_secret = resolve_credentials(args)

    # ── Validate inputs ────────────────────────────────────────────────────────
    try:
        params = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(f"\n✗  Validation error: {exc}\n")
        logger.error("Validation error: %s", exc)
        sys.exit(1)

    # ── Print summary ──────────────────────────────────────────────────────────
    print_order_summary(
        symbol=params["symbol"],
        side=params["side"],
        order_type=params["order_type"],
        quantity=params["quantity"],
        price=params["price"],
        stop_price=params["stop_price"],
    )

    # ── Create client ──────────────────────────────────────────────────────────
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        print(f"\n✗  Client init error: {exc}\n")
        sys.exit(1)

    # ── Connectivity check ─────────────────────────────────────────────────────
    try:
        server_time = client.get_server_time()
        logger.info("Server time: %s", server_time)
    except BinanceNetworkError as exc:
        print(f"\n✗  Cannot reach Binance testnet: {exc}\n")
        logger.error("Connectivity check failed: %s", exc)
        sys.exit(1)
    except BinanceAPIError as exc:
        print(f"\n✗  Binance API error on connectivity check: {exc}\n")
        logger.error("API error on connectivity check: %s", exc)
        sys.exit(1)

    # ── Place order ────────────────────────────────────────────────────────────
    result = place_order(
        client=client,
        symbol=params["symbol"],
        side=params["side"],
        order_type=params["order_type"],
        quantity=params["quantity"],
        price=params["price"],
        stop_price=params["stop_price"],
    )

    print_order_result(result)

    if not result.success:
        logger.error("Order placement failed: %s", result.error_message)
        sys.exit(1)

    logger.info("Bot run completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
