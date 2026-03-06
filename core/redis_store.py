"""Write snapshots and orderbook tops to Redis."""

import orjson
import redis.asyncio as redis
from core.config import AVG_NET_RETENTION_MINUTES, REDIS_URL
from core.models import ArbitrageSnapshot, OrderBookTop

# Sorted set: score = minute_ts (unix // 60), member = avg_net_bps string. One ZRANGE for full history.
AVG_NET_KEY = "arb:avg_net:minutely"


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


async def save_avg_net_minutely(
    client: redis.Redis,
    minute_ts: int,
    avg_net_bps: float,
) -> None:
    """
    Append one minute's average net (bps) to the time series. Keeps last AVG_NET_RETENTION_MINUTES.
    Uses sorted set: score = minute_ts, member = avg string. Fast single ZRANGE for charts.
    """
    # Member must be unique per minute; use "minute_ts:avg" so charts can parse (score=minute_ts, member=ts:avg)
    member = f"{minute_ts}:{avg_net_bps:.4f}"
    await client.zremrangebyscore(AVG_NET_KEY, minute_ts, minute_ts)
    await client.zadd(AVG_NET_KEY, {member: minute_ts})
    # Keep only last N minutes
    cutoff = minute_ts - AVG_NET_RETENTION_MINUTES
    await client.zremrangebyscore(AVG_NET_KEY, "-inf", cutoff)
    # Optional: key TTL so data expires if dashboard stops (retention + 1h buffer)
    await client.expire(AVG_NET_KEY, AVG_NET_RETENTION_MINUTES * 60 + 3600)


async def get_avg_net_series(client: redis.Redis) -> list[tuple[int, float]]:
    """
    Read full minute series for charts. One ZRANGE, O(log N + M). Returns [(minute_ts, avg_bps), ...] in time order.
    Parse member as "minute_ts:avg_bps" (or score is minute_ts, member suffix is avg).
    """
    raw = await client.zrange(AVG_NET_KEY, 0, -1, withscores=True)
    out: list[tuple[int, float]] = []
    for member, score in raw:
        minute_ts = int(score)
        s = member.decode() if isinstance(member, bytes) else member
        try:
            _, avg_str = s.split(":", 1)
            avg_bps = float(avg_str)
        except (ValueError, IndexError):
            continue
        out.append((minute_ts, avg_bps))
    return out
