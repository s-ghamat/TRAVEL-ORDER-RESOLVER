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

    # station-level candidates for UI disambiguation
    departure_candidates: Optional[List[Station]] = None
    arrival_candidates: Optional[List[Station]] = None

    # when invalid, propose options + question
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
    s = (sentence or "").lower()
    dep_l = (dep or "").lower()
    arr_l = (arr or "").lower()

    dep_in = dep_l in s
    arr_in = arr_l in s

    if dep_in and arr_in:
        conf = 0.92
    elif dep_in or arr_in:
        conf = 0.82
    else:
        conf = 0.75

    dbg = {
        "confidence_heuristic": "literal_presence",
        "departure_literal_in_sentence": dep_in,
        "arrival_literal_in_sentence": arr_in,
    }
    return conf, dbg


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

        # ---------- INVALID / ambiguous ----------
        if result is None:
            if not helpful:
                return ResolveResult(
                    ok=False,
                    confidence=0.15,
                    debug={"reason": "invalid_or_ambiguous", "mode": mode, "resolver": "tor.nlp.parse_order"},
                )

            # propose likely stations from free text
            cands = station_candidates_from_free_text(stations_df, s, limit=12)

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
                    "mode": mode,
                    "resolver": "tor.nlp.parse_order",
                    "proposed_candidates_count": len(cands),
                },
            )

        # ---------- Valid ----------
        dep, arr = result
        conf, conf_dbg = _basic_confidence(s, dep, arr)

        dep_cands = station_candidates_for_city(stations_df, dep)
        arr_cands = station_candidates_for_city(stations_df, arr)

        # penalize heavy ambiguity
        ambiguity_penalty = 0.0
        if len(dep_cands) >= 6:
            ambiguity_penalty += 0.07
        if len(arr_cands) >= 6:
            ambiguity_penalty += 0.07
        conf = max(0.0, conf - ambiguity_penalty)

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
            },
        )

    if mode == "spacy":
        return ResolveResult(ok=False, confidence=0.0, debug={"reason": "spacy_mode_not_connected_yet", "mode": mode})

    return ResolveResult(ok=False, confidence=0.0, debug={"reason": "unknown_mode", "mode": mode})
