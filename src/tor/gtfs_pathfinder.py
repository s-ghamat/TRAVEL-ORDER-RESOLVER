from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List
import re

import pandas as pd


GTFS_DIR_DEFAULT = Path("data/gtfs_sncf")


@dataclass(frozen=True)
class DirectJourney:
    from_stop_id: str
    to_stop_id: str
    trip_id: str
    route_id: str
    departure_time: str
    arrival_time: str
    from_stop_name: str
    to_stop_name: str


@dataclass(frozen=True)
class OneTransferJourney:
    trip1_id: str
    route1_id: str
    from_stop_id: str
    transfer_stop_id: str
    dep1_time: str
    arr1_time: str

    trip2_id: str
    route2_id: str
    to_stop_id: str
    dep2_time: str
    arr2_time: str

    from_stop_name: str
    transfer_stop_name: str
    to_stop_name: str


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[’']", " ", s)
    s = re.sub(r"[^a-z0-9àâçéèêëîïôùûüÿñæœ\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_uic_candidates(uic_field: str) -> List[str]:
    if not uic_field:
        return []
    parts = re.split(r"[;,\s]+", str(uic_field))
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if re.fullmatch(r"\d{8}", p):
            out.append(p)
    return out


def _extract_uic_from_stop_id(stop_id: str) -> Optional[str]:
    if not stop_id:
        return None
    m = re.search(r"(\d{8})", stop_id)
    return m.group(1) if m else None


class GtfsIndex:
    def __init__(self, gtfs_dir: Path):
        self.gtfs_dir = gtfs_dir
        self.stops = pd.read_csv(gtfs_dir / "stops.txt", dtype=str).fillna("")
        self.stop_times = pd.read_csv(gtfs_dir / "stop_times.txt", dtype=str).fillna("")
        self.trips = pd.read_csv(gtfs_dir / "trips.txt", dtype=str).fillna("")
        self.routes = pd.read_csv(gtfs_dir / "routes.txt", dtype=str).fillna("")

        self.stops["stop_name_norm"] = self.stops["stop_name"].astype(str).map(_norm)

        # stop_id -> stop_name
        self.stop_name_by_id: Dict[str, str] = dict(
            zip(self.stops["stop_id"].astype(str), self.stops["stop_name"].astype(str))
        )

        # trip_id -> route_id
        self.route_by_trip: Dict[str, str] = dict(
            zip(self.trips["trip_id"].astype(str), self.trips["route_id"].astype(str))
        )

        # ------------------------------------------------------------
        # Build UIC -> stop_id map using stop_code first
        # ------------------------------------------------------------
        uic_map: Dict[str, List[str]] = {}

        # 1) stop_code 
        if "stop_code" in self.stops.columns:
            for _, r in self.stops.iterrows():
                stop_id = str(r["stop_id"])
                stop_code = str(r["stop_code"]).strip()
                if re.fullmatch(r"\d{8}", stop_code):
                    uic_map.setdefault(stop_code, []).append(stop_id)

        # 2) fallback: extract from stop_id digits
        if not uic_map:
            for sid in self.stops["stop_id"].astype(str).tolist():
                uic = _extract_uic_from_stop_id(sid)
                if uic:
                    uic_map.setdefault(uic, []).append(sid)

        # ensure unique
        for k in list(uic_map.keys()):
            uic_map[k] = list(dict.fromkeys(uic_map[k]))

        self.stop_ids_by_uic = uic_map


def load_gtfs(gtfs_dir: Path = GTFS_DIR_DEFAULT) -> GtfsIndex:
    return GtfsIndex(gtfs_dir)


def resolve_stop_ids_for_station(
    gtfs: GtfsIndex,
    station_name: str,
    uic_field: Optional[str] = None,
    max_results: int = 20,
) -> List[str]:
    stop_ids: List[str] = []

    # 1) UIC mapping
    if uic_field:
        for uic in _extract_uic_candidates(uic_field):
            stop_ids.extend(gtfs.stop_ids_by_uic.get(uic, []))

    stop_ids = list(dict.fromkeys(stop_ids))
    if stop_ids:
        return stop_ids[:max_results]

    # 2) fallback: stop_name substring match
    q = _norm(station_name)
    if not q:
        return []
    sub = gtfs.stops[gtfs.stops["stop_name_norm"].str.contains(re.escape(q), na=False)]
    if sub.empty:
        return []
    return sub["stop_id"].astype(str).head(max_results).tolist()


def find_direct_journeys(
    gtfs: GtfsIndex,
    from_stop_ids: List[str],
    to_stop_ids: List[str],
    limit: int = 5,
) -> List[DirectJourney]:
    if not from_stop_ids or not to_stop_ids:
        return []

    st = gtfs.stop_times

    st_from = st[st["stop_id"].isin(from_stop_ids)][["trip_id", "stop_id", "stop_sequence", "departure_time"]].copy()
    st_to = st[st["stop_id"].isin(to_stop_ids)][["trip_id", "stop_id", "stop_sequence", "arrival_time"]].copy()

    if st_from.empty or st_to.empty:
        return []

    merged = st_from.merge(st_to, on="trip_id", suffixes=("_from", "_to"))

    merged["seq_from"] = pd.to_numeric(merged["stop_sequence_from"], errors="coerce")
    merged["seq_to"] = pd.to_numeric(merged["stop_sequence_to"], errors="coerce")
    merged = merged[merged["seq_from"].notna() & merged["seq_to"].notna()]
    merged = merged[merged["seq_from"] < merged["seq_to"]]

    if merged.empty:
        return []

    merged = merged.sort_values("departure_time").head(200)

    out: List[DirectJourney] = []
    for _, r in merged.iterrows():
        trip_id = str(r["trip_id"])
        route_id = gtfs.route_by_trip.get(trip_id, "")

        from_sid = str(r["stop_id_from"])
        to_sid = str(r["stop_id_to"])

        out.append(
            DirectJourney(
                from_stop_id=from_sid,
                to_stop_id=to_sid,
                trip_id=trip_id,
                route_id=route_id,
                departure_time=str(r["departure_time"]),
                arrival_time=str(r["arrival_time"]),
                from_stop_name=gtfs.stop_name_by_id.get(from_sid, from_sid),
                to_stop_name=gtfs.stop_name_by_id.get(to_sid, to_sid),
            )
        )
        if len(out) >= limit:
            break

    return out


def find_one_transfer_journeys(
    gtfs: GtfsIndex,
    from_stop_ids: List[str],
    to_stop_ids: List[str],
    limit: int = 3,
    max_candidates_per_leg: int = 400,
) -> List[OneTransferJourney]:
    if not from_stop_ids or not to_stop_ids:
        return []

    st = gtfs.stop_times

    # LEG 1: from_stop -> transfer_stop
    st_from = st[st["stop_id"].isin(from_stop_ids)][["trip_id", "stop_id", "stop_sequence", "departure_time"]].copy()
    if st_from.empty:
        return []

    st_leg1_all = st[["trip_id", "stop_id", "stop_sequence", "arrival_time"]].copy()
    leg1 = st_from.merge(st_leg1_all, on="trip_id", suffixes=("_from", "_x"))
    leg1["seq_from"] = pd.to_numeric(leg1["stop_sequence_from"], errors="coerce")
    leg1["seq_x"] = pd.to_numeric(leg1["stop_sequence_x"], errors="coerce")
    leg1 = leg1[leg1["seq_from"].notna() & leg1["seq_x"].notna()]
    leg1 = leg1[leg1["seq_from"] < leg1["seq_x"]]
    leg1 = leg1[leg1["stop_id_x"] != leg1["stop_id_from"]]
    if leg1.empty:
        return []

    leg1 = leg1.sort_values("departure_time").head(max_candidates_per_leg)
    leg1 = leg1.rename(
        columns={
            "stop_id_from": "from_stop_id",
            "departure_time": "dep1_time",
            "stop_id_x": "transfer_stop_id",
            "arrival_time": "arr1_time",
        }
    )[["trip_id", "from_stop_id", "transfer_stop_id", "dep1_time", "arr1_time"]]

    # LEG 2: transfer_stop -> to_stop
    st_to = st[st["stop_id"].isin(to_stop_ids)][["trip_id", "stop_id", "stop_sequence", "arrival_time"]].copy()
    if st_to.empty:
        return []

    st_leg2_all = st[["trip_id", "stop_id", "stop_sequence", "departure_time"]].copy()
    leg2 = st_leg2_all.merge(st_to, on="trip_id", suffixes=("_x", "_to"))
    leg2["seq_x"] = pd.to_numeric(leg2["stop_sequence_x"], errors="coerce")
    leg2["seq_to"] = pd.to_numeric(leg2["stop_sequence_to"], errors="coerce")
    leg2 = leg2[leg2["seq_x"].notna() & leg2["seq_to"].notna()]
    leg2 = leg2[leg2["seq_x"] < leg2["seq_to"]]
    leg2 = leg2[leg2["stop_id_x"] != leg2["stop_id_to"]]
    if leg2.empty:
        return []

    leg2 = leg2.sort_values("departure_time").head(max_candidates_per_leg)
    leg2 = leg2.rename(
        columns={
            "stop_id_x": "transfer_stop_id",
            "departure_time": "dep2_time",
            "stop_id_to": "to_stop_id",
            "arrival_time": "arr2_time",
        }
    )[["trip_id", "transfer_stop_id", "to_stop_id", "dep2_time", "arr2_time"]]

    # JOIN on transfer_stop_id and time order dep2 >= arr1
    joined = leg1.merge(leg2, on="transfer_stop_id", suffixes=("_1", "_2"))
    if joined.empty:
        return []

    joined = joined[joined["dep2_time"] >= joined["arr1_time"]]
    if joined.empty:
        return []

    joined = joined.sort_values(["dep1_time", "arr2_time"]).head(200)

    out: List[OneTransferJourney] = []
    for _, r in joined.iterrows():
        trip1 = str(r["trip_id_1"])
        trip2 = str(r["trip_id_2"])
        from_sid = str(r["from_stop_id"])
        transfer_sid = str(r["transfer_stop_id"])
        to_sid = str(r["to_stop_id"])

        out.append(
            OneTransferJourney(
                trip1_id=trip1,
                route1_id=gtfs.route_by_trip.get(trip1, ""),
                from_stop_id=from_sid,
                transfer_stop_id=transfer_sid,
                dep1_time=str(r["dep1_time"]),
                arr1_time=str(r["arr1_time"]),
                trip2_id=trip2,
                route2_id=gtfs.route_by_trip.get(trip2, ""),
                to_stop_id=to_sid,
                dep2_time=str(r["dep2_time"]),
                arr2_time=str(r["arr2_time"]),
                from_stop_name=gtfs.stop_name_by_id.get(from_sid, from_sid),
                transfer_stop_name=gtfs.stop_name_by_id.get(transfer_sid, transfer_sid),
                to_stop_name=gtfs.stop_name_by_id.get(to_sid, to_sid),
            )
        )
        if len(out) >= limit:
            break

    return out
