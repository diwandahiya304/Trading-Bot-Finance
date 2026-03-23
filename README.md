# Binance Futures Trading Bot

A lightweight Python CLI application for placing orders on the **Binance Futures Demo Trading environment (USDT-M)**. Built with a clean, layered architecture: a raw REST client, an order-logic layer, an input-validation layer, and an `argparse`-powered CLI.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (signing, HTTP, error handling)
│   ├── orders.py          # Order payload builders + OrderResult dataclass
│   ├── validators.py      # CLI input validation
│   └── logging_config.py  # Structured logging (file + console)
├── cli.py                 # CLI entry point (argparse)
├── logs/                  # Auto-created; log files land here
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Prerequisites

- Python 3.9 or later
- A Binance account with **Demo Trading** enabled
- Demo Trading API credentials from: https://www.binance.com/en/my/settings/api-management (switch to Demo Trading mode first)

### 2. Clone the repository

```bash
git clone https://github.com/diwandahiya304/Trading-Bot-Finance.git
cd Trading-Bot-Finance
```

### 3. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Set your API credentials

**Linux / macOS:**
```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_secret_key_here"
```

**Windows:**
```cmd
set BINANCE_API_KEY=your_api_key_here
set BINANCE_API_SECRET=your_secret_key_here
```

Or pass them directly on each command with `--api-key` / `--api-secret`.

---

## How to Run

### General syntax

```
python cli.py --symbol SYMBOL --side SIDE --type TYPE --qty QUANTITY [OPTIONS]
```

### Examples

#### Market BUY

```cmd
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.002
```

**Output:**
```
════════════════════════════════════════════════════
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.002
════════════════════════════════════════════════════

════════════════════════════════════════════════════
  ✓  ORDER PLACED SUCCESSFULLY
────────────────────────────────────────────────────
  Order ID       : 12953367215
  Client Ord ID  : hDKTLnUHqV6Dz12wgTSLek
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Status         : NEW
  Orig Qty       : 0.002
  Executed Qty   : 0.000
════════════════════════════════════════════════════
```

#### Limit SELL (price required)

```cmd
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --qty 0.002 --price 120000
```

#### Stop-Market SELL — bonus order type (code supported, may vary by environment)

```cmd
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.002 --stop-price 80000
```

#### Pass credentials inline

```cmd
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET --symbol BTCUSDT --side BUY --type MARKET --qty 0.002
```

#### Change log verbosity

```cmd
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.002 --log-level INFO
```

---

## CLI Reference

| Flag | Required | Description |
|---|---|---|
| `--symbol` | ✓ | Trading pair, e.g. `BTCUSDT` |
| `--side` | ✓ | `BUY` or `SELL` |
| `--type` | ✓ | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--qty` | ✓ | Order quantity (float) |
| `--price` | LIMIT only | Limit price |
| `--stop-price` | STOP_MARKET only | Trigger price |
| `--api-key` | ✗ | Overrides `BINANCE_API_KEY` env var |
| `--api-secret` | ✗ | Overrides `BINANCE_API_SECRET` env var |
| `--log-level` | ✗ | `DEBUG` (default), `INFO`, `WARNING`, `ERROR` |

---

## Logging

Logs are written to `logs/trading_bot_YYYYMMDD.log` automatically.

- **File handler** — captures `DEBUG` and above (full API request/response detail)
- **Console handler** — shows `WARNING` and above (keeps terminal output clean)

Each log line format:
```
YYYY-MM-DD HH:MM:SS | LEVEL    | module | message
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing/invalid CLI argument | Validation error printed; non-zero exit |
| Price missing for LIMIT order | Validation error before any network call |
| Network timeout / connection failure | `BinanceNetworkError` caught; error printed |
| Binance API error (e.g. invalid symbol) | `BinanceAPIError` caught; HTTP code + message printed |
| Missing credentials | Clear message listing what is missing; non-zero exit |

---

## Assumptions

1. **Demo Trading environment** — the base URL is set to `https://demo-fapi.binance.com`. For the classic testnet (`testnet.binancefuture.com`) or production, change `TESTNET_BASE_URL` in `bot/client.py`.
2. **LIMIT orders use `timeInForce=GTC`** (Good Till Cancelled) by default.
3. Quantity and price precision validation (lot size / tick size filters) is delegated to the Binance API rather than implemented client-side, to avoid maintaining stale filter tables.
4. Minimum order notional on BTCUSDT is $100 — use at least `qty=0.002` at current BTC prices.
5. No dependency on `python-binance`; all API calls are made with plain `requests` for transparency and minimal footprint.

---

## Dependencies

```
requests>=2.31.0
```

Python standard library only otherwise (`argparse`, `hmac`, `hashlib`, `logging`, `dataclasses`, `os`, `time`).
