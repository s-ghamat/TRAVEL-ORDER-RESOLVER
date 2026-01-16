from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import math
from api.stations import Station


@dataclass(frozen=True)
class RouteStep:
    label: str
    station: Station
    distance_km_from_prev: float = 0.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Earth radius in km
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def build_itinerary(
    departure: Station,
    arrival: Station,
    via: Optional[List[Station]] = None,
) -> List[RouteStep]:
    """
    Simple, explainable pathfinder:
    returns the ordered list of stations (departure -> via... -> arrival)
    with distance between consecutive points.

    This satisfies “sequence of routing points” even before SNCF schedule APIs.
    """
    via = via or []
    ordered = [departure] + via + [arrival]

    steps: List[RouteStep] = []
    prev = None
    for i, st in enumerate(ordered):
        if prev is None:
            steps.append(RouteStep(label="Départ", station=st, distance_km_from_prev=0.0))
        else:
            d = _haversine_km(prev.latitude, prev.longitude, st.latitude, st.longitude)
            label = "Étape" if i < len(ordered) - 1 else "Arrivée"
            steps.append(RouteStep(label=label, station=st, distance_km_from_prev=float(d)))
        prev = st

    return steps
