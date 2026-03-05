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


REDIS_URL: str = _get("REDIS_URL", "redis://redis:6379/0")
BYBIT_WS_PUBLIC_SPOT: str = _get(
    "BYBIT_WS_PUBLIC_SPOT", "wss://stream.bybit.com/v5/public/spot"
)

SYMBOLS_STR: str = _get("SYMBOLS", "BTCUSDT,ETHUSDT,ETHBTC,SOLUSDT,SOLBTC,SOLETH")
SYMBOLS: list[str] = [s.strip() for s in SYMBOLS_STR.split(",") if s.strip()]

TAKER_FEE_BPS: float = _get_float("TAKER_FEE_BPS", 5.5)
SLIPPAGE_BPS_BUFFER: float = _get_float("SLIPPAGE_BPS_BUFFER", 10)

PRINT_EVERY_SEC: float = _get_float("PRINT_EVERY_SEC", 1)
TOP_N: int = _get_int("TOP_N", 15)
EDGE_THRESHOLD_BPS: float = _get_float("EDGE_THRESHOLD_BPS", 2)
MAX_STALE_MS: int = _get_int("MAX_STALE_MS", 1500)
