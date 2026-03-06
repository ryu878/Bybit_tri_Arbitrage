"""Build scanner paths and reverse index from Triangle list."""

from core.models import ScannerPath, Triangle


def build_paths_and_index(triangles: list[Triangle]) -> tuple[list[ScannerPath], dict[str, list[int]]]:
    """
    Build list of ScannerPath and symbol -> list of path indices.
    Each symbol maps to indices of paths that use it.
    """
    paths: list[ScannerPath] = []
    symbol_to_indices: dict[str, list[int]] = {}

    for t in triangles:
        if len(t.legs) != 3:
            continue
        (s1, side1), (s2, side2), (s3, side3) = t.legs
        label = t.path_str or f"{s1}|{s2}|{s3}"
        path = ScannerPath(
            label=label,
            s1=s1,
            side1=side1.upper() if side1 else "BUY",
            s2=s2,
            side2=side2.upper() if side2 else "BUY",
            s3=s3,
            side3=side3.upper() if side3 else "SELL",
        )
        idx = len(paths)
        paths.append(path)
        for sym in (s1, s2, s3):
            symbol_to_indices.setdefault(sym, []).append(idx)

    return paths, symbol_to_indices
