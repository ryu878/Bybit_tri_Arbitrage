"""Load .env and expose configuration values."""

import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _get_float(key: str, default: float = 0.0) -> float:
    try:
        return float(_get(key) or default)
    except ValueError:
        return default


def _get_int(key: str, default: int = 0) -> int:
    try:
        return int(_get(key) or default)
    except ValueError:
        return default


def _get_bool(key: str, default: bool = False) -> bool:
    v = _get(key).lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off", ""):
        return False
    return default


REDIS_URL: str = _get("REDIS_URL", "redis://redis:6379/0")
# Bybit WebSocket: pybit uses this to choose mainnet vs testnet
BYBIT_TESTNET: bool = _get_bool("BYBIT_TESTNET", False)

# Triangle start coins (paths start from these). Comma-separated, e.g. USDT,BTC,ETH,USDC
TRIANGLE_START_COINS_STR: str = _get("TRIANGLE_START_COINS", "USDT,BTC,ETH,USDC")
TRIANGLE_START_COINS: set[str] = {
    s.strip().upper() for s in TRIANGLE_START_COINS_STR.split(",") if s.strip()
}

TAKER_FEE_BPS: float = _get_float("TAKER_FEE_BPS", 5.5)
SLIPPAGE_BPS_BUFFER: float = _get_float("SLIPPAGE_BPS_BUFFER", 10)

PRINT_EVERY_SEC: float = _get_float("PRINT_EVERY_SEC", 1)
TOP_N: int = _get_int("TOP_N", 15)
EDGE_THRESHOLD_BPS: float = _get_float("EDGE_THRESHOLD_BPS", 2)
MAX_STALE_MS: int = _get_int("MAX_STALE_MS", 1500)

# Telegram (optional): leave empty to disable
TELEGRAM_BOT_TOKEN: str = _get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = _get("TELEGRAM_CHAT_ID", "")

# Debug: print data collection, calculations, etc. to console
DEBUG_MODE: bool = _get_bool("DEBUG_MODE", False)

# Save average net edge to Redis every minute (for charts / moving averages)
SAVE_TO_DB: bool = _get_bool("SAVE_TO_DB", False)
# Keep last N minutes (1440 = 24h); used for Redis trim and optional key TTL
AVG_NET_RETENTION_MINUTES: int = _get_int("AVG_NET_RETENTION_MINUTES", 1440)
