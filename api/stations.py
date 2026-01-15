from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re
import pandas as pd


@dataclass(frozen=True)
class Station:
    station_name: str
    uic_code: str
    latitude: float
    longitude: float


def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[’']", " ", s)
    s = re.sub(r"[^a-zàâçéèêëîïôùûüÿñæœ0-9\s\-]", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_stations(csv_path: Path) -> pd.DataFrame:
    """
    Loads your cleaned stations CSV.
    Expected columns:
      - station_name
      - uic_code
      - latitude
      - longitude
    """
    df = pd.read_csv(csv_path)
    for col in ["station_name", "uic_code", "latitude", "longitude"]:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' in {csv_path}")
    df = df.copy()
    df["station_norm"] = df["station_name"].astype(str).map(_normalize)
    return df


def station_candidates_for_city(
    stations_df: pd.DataFrame,
    city: str,
    limit: int = 12,
) -> List[Station]:
    """
    Return likely station candidates for a city name.
    Strategy (simple + explainable):
      1) substring match: station_norm contains city_norm as a whole word
      2) rank: stations with 'gare' / main hub keywords first, then by name length
    """
    city_norm = _normalize(city)
    if not city_norm:
        return []
    pattern = rf"(?:^|\s){re.escape(city_norm)}(?:\s|$)"
    mask = stations_df["station_norm"].str.contains(pattern, regex=True, na=False)

    sub = stations_df[mask].copy()
    if sub.empty:
        return []

    # Heuristic ranking
    def score(name_norm: str) -> int:
        sc = 0
        if name_norm.startswith(city_norm + " "):
            sc += 20
        for kw, pts in [
            ("gare", 10),
            ("part dieu", 8),
            ("perrache", 7),
            ("saint", 2),
            ("st", 2),
            ("centre", 2),
        ]:
            if kw in name_norm:
                sc += pts
        sc += max(0, 12 - min(len(name_norm), 60) // 5)
        return sc

    sub["rank_score"] = sub["station_norm"].map(score)
    sub = sub.sort_values(["rank_score", "station_name"], ascending=[False, True]).head(limit)

    out: List[Station] = []
    for _, r in sub.iterrows():
        out.append(
            Station(
                station_name=str(r["station_name"]),
                uic_code=str(r["uic_code"]),
                latitude=float(r["latitude"]),
                longitude=float(r["longitude"]),
            )
        )
    return out


def find_station_by_uic(stations_df: pd.DataFrame, uic_code: str) -> Optional[Station]:
    if not uic_code:
        return None
    sub = stations_df[stations_df["uic_code"].astype(str) == str(uic_code)]
    if sub.empty:
        return None
    r = sub.iloc[0]
    return Station(
        station_name=str(r["station_name"]),
        uic_code=str(r["uic_code"]),
        latitude=float(r["latitude"]),
        longitude=float(r["longitude"]),
    )
