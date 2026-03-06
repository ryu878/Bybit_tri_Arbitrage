"""Debug console output when DEBUG_MODE is true."""

import sys
from core.config import DEBUG_MODE


def debug_log(tag: str, message: str) -> None:
    """Print to stderr when DEBUG_MODE is True. tag e.g. 'WS', 'SCAN', 'REDIS'."""
    if not DEBUG_MODE:
        return
    print(f"[DEBUG][{tag}] {message}", file=sys.stderr, flush=True)
