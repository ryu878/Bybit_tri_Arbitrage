"""Fetch Bybit spot instruments and filter to valid (trading) symbols."""

import httpx

from core.config import BYBIT_TESTNET
from core.debug_log import debug_log

BYBIT_REST_MAINNET = "https://api.bybit.com"
BYBIT_REST_TESTNET = "https://api-testnet.bybit.com"


def get_valid_spot_symbols(timeout: float = 10.0) -> set[str]:
    """
    Return the set of spot symbols that are currently tradeable on Bybit.
    Uses GET /v5/market/instruments-info?category=spot; only symbols with status 'Trading' are included.
    """
    base = BYBIT_REST_TESTNET if BYBIT_TESTNET else BYBIT_REST_MAINNET
    url = f"{base}/v5/market/instruments-info"
    params = {"category": "spot"}
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        debug_log("SYMBOLS", f"Failed to fetch spot instruments: {e}")
        return set()
    result = data.get("result") or {}
    lst = result.get("list") or []
    valid = {item["symbol"] for item in lst if item.get("status") == "Trading"}
    return valid


def filter_valid_symbols(requested: list[str]) -> tuple[list[str], list[str]]:
    """
    Check which requested symbols are valid on Bybit spot.
    Returns (valid_symbols, invalid_symbols).
    If the API call fails, returns (requested, []) so we still run with configured symbols.
    """
    valid_set = get_valid_spot_symbols()
    if not valid_set:
        # API failed or returned nothing; use all requested and log
        debug_log("SYMBOLS", "Could not fetch Bybit spot instruments; using all configured symbols.")
        return (list(requested), [])
    valid_list = [s for s in requested if s in valid_set]
    invalid_list = [s for s in requested if s not in valid_set]
    return (valid_list, invalid_list)
