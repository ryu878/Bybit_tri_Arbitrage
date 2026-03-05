"""Define triangular cycles and mapping from symbol -> triangles using it."""

from core.models import Triangle


def build_triangles(symbols: list[str]) -> list[Triangle]:
    """
    Build all triangular cycles from the symbol list.
    Example: USDT -> BTC -> ETH -> USDT using BTCUSDT, ETHBTC, ETHUSDT.
    Each triangle has 3 legs: (symbol, "buy" | "sell").
    """
    triangles: list[Triangle] = []
    usdt_pairs = [s for s in symbols if s.endswith("USDT")]
    cross_pairs = [s for s in symbols if s not in usdt_pairs]

    for pa in usdt_pairs:
        for pb in usdt_pairs:
            if pa == pb:
                continue
            base_a = pa.replace("USDT", "")
            base_b = pb.replace("USDT", "")
            need_ab = base_a + base_b
            need_ba = base_b + base_a

            for c in cross_pairs:
                if c != need_ab and c != need_ba:
                    continue

                # Triangle A: start USDT -> pa (get base_a) -> c -> pb (get USDT)
                # leg1: buy pa (USDT -> base_a), leg2: trade c (base_a <-> base_b), leg3: sell pb (base_b -> USDT)
                if c == need_ba:
                    # base_a -> base_b: we have base_a, get base_b = buy c (e.g. buy ETHBTC = give BTC get ETH)
                    tid_a = "|".join([pa, c, pb])
                    legs_a = [(pa, "buy"), (c, "buy"), (pb, "sell")]
                else:
                    # c == need_ab: base_a -> base_b = sell c (e.g. sell BTCETH = give BTC get ETH)
                    tid_a = "|".join([pa, c, pb])
                    legs_a = [(pa, "buy"), (c, "sell"), (pb, "sell")]

                triangles.append(Triangle(id=tid_a, legs=legs_a))

                # Triangle B: start USDT -> pb (get base_b) -> c -> pa (get USDT)
                if c == need_ab:
                    tid_b = "|".join([pb, c, pa])
                    legs_b = [(pb, "buy"), (c, "buy"), (pa, "sell")]
                else:
                    tid_b = "|".join([pb, c, pa])
                    legs_b = [(pb, "buy"), (c, "sell"), (pa, "sell")]

                triangles.append(Triangle(id=tid_b, legs=legs_b))

    return triangles


def symbol_to_triangles(symbols: list[str]) -> dict[str, list[Triangle]]:
    """Map each symbol to the list of triangles that use it."""
    all_triangles = build_triangles(symbols)
    out: dict[str, list[Triangle]] = {s: [] for s in symbols}
    for t in all_triangles:
        for sym, _ in t.legs:
            if sym in out:
                out[sym].append(t)
    return out
