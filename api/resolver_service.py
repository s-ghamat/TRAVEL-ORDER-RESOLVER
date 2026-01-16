from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from api.stations import (
    load_stations,
    station_candidates_for_city,
    station_candidates_from_free_text,
    Station,
)

STATIONS_CSV = PROJECT_ROOT / "data" / "sncf_clean" / "stations_clean.csv"


@dataclass
class ResolveResult:
    ok: bool
    departure: Optional[str] = None
    arrival: Optional[str] = None
    confidence: float = 0.0

    departure_candidates: Optional[List[Station]] = None
    arrival_candidates: Optional[List[Station]] = None

    followup_question: Optional[str] = None
    proposed_candidates: Optional[List[Station]] = None

    debug: Optional[Dict[str, Any]] = None


_STATIONS_DF: Optional[pd.DataFrame] = None


def _get_stations_df() -> pd.DataFrame:
    global _STATIONS_DF
    if _STATIONS_DF is None:
        _STATIONS_DF = load_stations(STATIONS_CSV)
    return _STATIONS_DF


def _basic_confidence(sentence: str, dep: str, arr: str) -> Tuple[float, Dict[str, Any]]:
    """
    Confidence baseline from literal presence.
    (Other penalties are applied later: ambiguity + contamination.)
    """
    s = (sentence or "").lower()
    dep_l = (dep or "").lower()
    arr_l = (arr or "").lower()

    dep_in = dep_l in s
    arr_in = arr_l in s

    if dep_in and arr_in:
        conf = 0.93
        strength = "both_literal"
    elif dep_in or arr_in:
        conf = 0.85
        strength = "one_literal"
    else:
        conf = 0.72
        strength = "none_literal"

    dbg = {
        "confidence_strength": strength,
        "departure_literal_in_sentence": dep_in,
        "arrival_literal_in_sentence": arr_in,
    }
    return conf, dbg


def _invalid_result_baseline(helpful: bool, stations_df: pd.DataFrame, sentence: str) -> ResolveResult:
    if not helpful:
        return ResolveResult(
            ok=False,
            confidence=0.15,
            debug={"reason": "invalid_or_ambiguous", "mode": "baseline", "resolver": "tor.nlp.parse_order"},
        )

    cands = station_candidates_from_free_text(stations_df, sentence, limit=12)
    q = (
        "Je n’ai pas compris la demande avec certitude.\n"
        "Peux-tu sélectionner la gare de départ et la gare d’arrivée parmi les suggestions ?"
    )
    return ResolveResult(
        ok=False,
        confidence=0.15,
        followup_question=q,
        proposed_candidates=cands,
        debug={
            "reason": "invalid_or_ambiguous_helpful_mode",
            "mode": "baseline",
            "resolver": "tor.nlp.parse_order",
            "proposed_candidates_count": len(cands),
        },
    )


def _invalid_result_spacy(helpful: bool, stations_df: pd.DataFrame, sentence: str) -> ResolveResult:
    if not helpful:
        return ResolveResult(
            ok=False,
            confidence=0.15,
            debug={"reason": "spacy_no_result", "mode": "spacy", "resolver": "tor.spacy_resolver.parse_order_spacy"},
        )

    cands = station_candidates_from_free_text(stations_df, sentence, limit=12)
    q = (
        "Je n’ai pas compris la demande avec certitude (spaCy).\n"
        "Peux-tu sélectionner la gare de départ et la gare d’arrivée parmi les suggestions ?"
    )
    return ResolveResult(
        ok=False,
        confidence=0.15,
        followup_question=q,
        proposed_candidates=cands,
        debug={
            "reason": "spacy_no_result_helpful",
            "mode": "spacy",
            "resolver": "tor.spacy_resolver.parse_order_spacy",
            "proposed_candidates_count": len(cands),
        },
    )


def _apply_ambiguity_and_contamination_penalties(
    conf: float,
    dep: str,
    arr: str,
    dep_cands: List[Station],
    arr_cands: List[Station],
) -> Tuple[float, float, float]:
    """
    Applies:
    - Ambiguity penalty: increases smoothly after 3 candidates
    - Contamination penalty: if the other city name appears inside candidate station names
    Returns: (new_conf, ambiguity_penalty, contamination_penalty)
    """
    dep_l = (dep or "").lower()
    arr_l = (arr or "").lower()

    # Smooth ambiguity penalty: starts after 3 candidates, grows 0.02 each extra, capped at 0.10 per side
    ambiguity_penalty = 0.0
    ambiguity_penalty += min(0.10, max(0.0, (len(dep_cands) - 3) * 0.02))
    ambiguity_penalty += min(0.10, max(0.0, (len(arr_cands) - 3) * 0.02))

    dep_names = " ".join([c.station_name.lower() for c in dep_cands])
    arr_names = " ".join([c.station_name.lower() for c in arr_cands])

    contamination_penalty = 0.0
    # If arrival city appears in departure candidates list => suspicious
    if arr_l and arr_l in dep_names:
        contamination_penalty += 0.05
    # If departure city appears in arrival candidates list => suspicious
    if dep_l and dep_l in arr_names:
        contamination_penalty += 0.05

    new_conf = max(0.0, conf - ambiguity_penalty - contamination_penalty)
    return new_conf, ambiguity_penalty, contamination_penalty


def resolve_sentence(sentence: str, mode: str = "baseline", helpful: bool = False) -> ResolveResult:
    s = (sentence or "").strip()
    if not s:
        return ResolveResult(ok=False, confidence=0.0, debug={"reason": "empty_input", "mode": mode})

    stations_df = _get_stations_df()

    if mode == "baseline":
        try:
            from tor.nlp import parse_order
        except Exception as e:
            return ResolveResult(
                ok=False,
                confidence=0.0,
                debug={"reason": "import_error", "mode": mode, "details": repr(e), "src_dir": str(SRC_DIR)},
            )

        result = parse_order(s)
        if result is None:
            return _invalid_result_baseline(helpful, stations_df, s)

        dep, arr = result
        conf, conf_dbg = _basic_confidence(s, dep, arr)

        dep_cands = station_candidates_for_city(stations_df, dep)
        arr_cands = station_candidates_for_city(stations_df, arr)

        conf, ambiguity_penalty, contamination_penalty = _apply_ambiguity_and_contamination_penalties(
            conf=conf,
            dep=dep,
            arr=arr,
            dep_cands=dep_cands,
            arr_cands=arr_cands,
        )

        return ResolveResult(
            ok=True,
            departure=dep,
            arrival=arr,
            confidence=conf,
            departure_candidates=dep_cands,
            arrival_candidates=arr_cands,
            debug={
                "mode": mode,
                "resolver": "tor.nlp.parse_order",
                **conf_dbg,
                "departure_candidates_count": len(dep_cands),
                "arrival_candidates_count": len(arr_cands),
                "ambiguity_penalty": ambiguity_penalty,
                "contamination_penalty": contamination_penalty,
            },
        )
    

    if mode == "spacy":
        try:
            from tor.spacy_resolver import parse_order_spacy
        except Exception as e:
            return ResolveResult(
                ok=False,
                confidence=0.0,
                debug={"reason": "import_error_spacy", "mode": mode, "details": repr(e), "src_dir": str(SRC_DIR)},
            )

        result = parse_order_spacy(s)
        if result is None:
            return _invalid_result_spacy(helpful, stations_df, s)

        dep, arr = result
        conf, conf_dbg = _basic_confidence(s, dep, arr)

        dep_cands = station_candidates_for_city(stations_df, dep)
        arr_cands = station_candidates_for_city(stations_df, arr)

        conf, ambiguity_penalty, contamination_penalty = _apply_ambiguity_and_contamination_penalties(
            conf=conf,
            dep=dep,
            arr=arr,
            dep_cands=dep_cands,
            arr_cands=arr_cands,
        )

        return ResolveResult(
            ok=True,
            departure=dep,
            arrival=arr,
            confidence=conf,
            departure_candidates=dep_cands,
            arrival_candidates=arr_cands,
            debug={
                "mode": mode,
                "resolver": "tor.spacy_resolver.parse_order_spacy",
                **conf_dbg,
                "departure_candidates_count": len(dep_cands),
                "arrival_candidates_count": len(arr_cands),
                "ambiguity_penalty": ambiguity_penalty,
                "contamination_penalty": contamination_penalty,
            },
        )

    return ResolveResult(ok=False, confidence=0.0, debug={"reason": "unknown_mode", "mode": mode})
