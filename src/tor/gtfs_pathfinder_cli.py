from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from tor.gtfs_pathfinder import (
    load_gtfs,
    find_direct_journeys,
    find_one_transfer_journeys,
    resolve_stop_ids_for_station,
)


def parse_triplet_line(line: str) -> Optional[tuple[str, str, str]]:
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


def load_station_uic_index(stations_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(stations_csv, dtype=str).fillna("")
    df["name_norm"] = df["station_name"].str.lower().str.strip()
    return df


def uic_for_city_guess(stations_df: pd.DataFrame, city: str) -> Optional[str]:
    """
    Choose a "best hub" station for a city using simple scoring.
    Crucial for schedule matching (GTFS).
    """
    c = (city or "").lower().strip()
    if not c:
        return None

    sub = stations_df[stations_df["name_norm"].str.startswith(c + " ", na=False)].copy()
    if sub.empty:
        sub = stations_df[stations_df["name_norm"].str.contains(c, na=False)].copy()
        if sub.empty:
            return None

    def score(name: str) -> int:
        n = (name or "").lower()

        if c == "paris" and "gare de lyon" in n:
            return 10_000
        if c == "lyon" and "part dieu" in n:
            return 9_000
        if c == "lyon" and "perrache" in n:
            return 8_000

        s = 0
        if "tgv" in n:
            s += 200
        if "gare" in n:
            s += 100
        if "centre" in n:
            s += 40

        if "halte" in n:
            s -= 60
        if "car" in n:
            s -= 80

        s += max(0, 30 - len(n) // 3)
        return s

    sub["hub_score"] = sub["station_name"].astype(str).map(score)
    sub = sub.sort_values("hub_score", ascending=False)

    return str(sub.iloc[0]["uic_code"])


def main() -> int:
    gtfs = load_gtfs(Path("data/gtfs_sncf"))

    stations_csv = Path("data/sncf_clean/stations_clean.csv")
    stations_df = load_station_uic_index(stations_csv)

    for raw in sys.stdin:
        parsed = parse_triplet_line(raw)
        if parsed is None:
            continue

        sid, dep_city, dest_city = parsed

        dep_uic = uic_for_city_guess(stations_df, dep_city)
        dest_uic = uic_for_city_guess(stations_df, dest_city)

        from_stop_ids = resolve_stop_ids_for_station(gtfs, dep_city, uic_field=dep_uic, max_results=30)
        to_stop_ids = resolve_stop_ids_for_station(gtfs, dest_city, uic_field=dest_uic, max_results=30)

        # --- Try DIRECT ---
        direct = find_direct_journeys(gtfs, from_stop_ids, to_stop_ids, limit=1)
        if direct:
            j = direct[0]

            # 1) STRICT spec route line (sequence of cities)
            print(f"{sid},{dep_city},{dest_city}", flush=True)

            # 2) Schedule details (extra line, demo)
            print(
                f"{sid},SCHEDULE,DIRECT,{dep_city},{dest_city},"
                f"{j.departure_time},{j.arrival_time},{j.trip_id},"
                f"{j.from_stop_name},{j.to_stop_name}",
                flush=True,
            )
            continue

        # --- Try 1 TRANSFER ---
        one = find_one_transfer_journeys(gtfs, from_stop_ids, to_stop_ids, limit=1)
        if one:
            j = one[0]
            print(f"{sid},{dep_city},{j.transfer_stop_name},{dest_city}", flush=True)

            # Schedule details 
            print(
                f"{sid},SCHEDULE,1_TRANSFER,{dep_city},{dest_city},"
                f"{j.dep1_time},{j.arr1_time},{j.trip1_id},"
                f"{j.dep2_time},{j.arr2_time},{j.trip2_id},"
                f"{j.from_stop_name},{j.transfer_stop_name},{j.to_stop_name}",
                flush=True,
            )
            continue

        print(f"{sid},NO_SCHEDULE_FOUND,{dep_city},{dest_city}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
