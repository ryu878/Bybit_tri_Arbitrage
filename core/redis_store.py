"""Write snapshots and orderbook tops to Redis."""

import orjson
import redis.asyncio as redis
from core.config import REDIS_URL
from core.models import ArbitrageSnapshot, OrderBookTop


async def get_redis() -> redis.Redis:
    """Return async Redis client (caller should close)."""
    return redis.from_url(REDIS_URL, decode_responses=False)


def _serialize_snapshot(snap: ArbitrageSnapshot) -> bytes:
    return orjson.dumps(
        {
            "triangle_id": snap.triangle_id,
            "path_str": snap.path_str,
            "raw_edge_bps": snap.raw_edge_bps,
            "edge_bps": snap.edge_bps,
            "leg1": snap.leg1,
            "leg2": snap.leg2,
            "leg3": snap.leg3,
            "end_amount": snap.end_amount,
            "timestamp": snap.timestamp,
            "start_amount": snap.start_amount,
        }
    )


async def write_tob(client: redis.Redis, top: OrderBookTop) -> None:
    """Store orderbook top for a symbol. Key: tob:{symbol}."""
    key = f"tob:{top.symbol}"
    payload = orjson.dumps(
        {
            "bid": top.bid,
            "bid_qty": top.bid_qty,
            "ask": top.ask,
            "ask_qty": top.ask_qty,
            "timestamp": top.timestamp,
        }
    )
    await client.set(key, payload)


async def write_arb_snapshot(client: redis.Redis, snap: ArbitrageSnapshot) -> None:
    """Store one arbitrage snapshot. Key: arb:snap:{triangle_id}."""
    key = f"arb:snap:{snap.triangle_id}"
    await client.set(key, _serialize_snapshot(snap))


async def write_arb_top(client: redis.Redis, snapshots: list[ArbitrageSnapshot]) -> None:
    """Store top arbitrage list. Key: arb:top."""
    payload = orjson.dumps(
        [
            {
                "triangle_id": s.triangle_id,
                "path_str": s.path_str,
                "raw_edge_bps": s.raw_edge_bps,
                "edge_bps": s.edge_bps,
                "leg1": s.leg1,
                "leg2": s.leg2,
                "leg3": s.leg3,
                "end_amount": s.end_amount,
                "timestamp": s.timestamp,
            }
            for s in snapshots
        ]
    )
    await client.set("arb:top", payload)
