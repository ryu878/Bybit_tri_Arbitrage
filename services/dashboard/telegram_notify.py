"""Send Telegram messages when arbitrage is found. Disabled if TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty."""

import httpx
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from core.models import ArbitrageSnapshot

TELEGRAM_API = "https://api.telegram.org"


def is_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def _format_message(snap: ArbitrageSnapshot) -> str:
    raw = round(snap.raw_edge_bps, 1)
    net = round(snap.edge_bps, 1)
    return f"Tri arb: {snap.path_str}\nraw {raw} bps | net {net} bps"


async def send_arb_notification(snap: ArbitrageSnapshot) -> bool:
    """Send one arbitrage snapshot to Telegram. Returns True if sent, False if disabled or error."""
    if not is_enabled():
        return False
    text = _format_message(snap)
    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            return r.is_success
    except Exception:
        return False
