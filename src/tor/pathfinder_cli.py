from __future__ import annotations

import sys
from typing import List, Optional


def build_route_cities(departure: str, destination: str) -> List[str]:
    """
    Minimal deterministic pathfinder (spec-compliant format):
    returns a 'sequence of cities' as a list.

    For now (before schedule/graph integration), we return the direct route:
      [Departure, Destination]
    Later, we will replace this with a real graph/schedule-based route.
    """
    departure = (departure or "").strip()
    destination = (destination or "").strip()
    if not departure or not destination:
        return []
    return [departure, destination]


def parse_triplet_line(line: str) -> Optional[tuple[str, str, str]]:
    """
    Input format: sentenceID,Departure,Destination
    """
    line = (line or "").strip()
    if not line:
        return None
    parts = [p.strip() for p in line.split(",", 2)]
    if len(parts) != 3:
        return None
    sid, dep, dest = parts
    if not sid or not dep or not dest:
        return None
    return sid, dep, dest


def main() -> int:
    """
    Reads triplets from stdin and prints route lines to stdout.
    Spec output: sentenceID,Departure,Step1,Step2,...,Destination
    Here: sentenceID,Departure,Destination (0 steps).
    """
    for raw in sys.stdin:
        parsed = parse_triplet_line(raw)
        if parsed is None:
            continue

        sid, dep, dest = parsed
        route = build_route_cities(dep, dest)

        if not route:
            print(f"{sid},INVALID_PATH", flush=True)
            continue
        print(",".join([sid] + route), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
