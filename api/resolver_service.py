from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@dataclass
class ResolveResult:
    ok: bool
    departure: Optional[str] = None
    arrival: Optional[str] = None
    confidence: float = 0.0
    debug: Optional[Dict[str, Any]] = None


def _basic_confidence(sentence: str, dep: str, arr: str) -> Tuple[float, Dict[str, Any]]:
    """
    Simple confidence heuristic (deterministic, explainable):
    - High if both city names are literally present in the sentence (normalized)
    - Medium otherwise (still valid via fuzzy match inside parse_order)
    """
    s = (sentence or "").lower()
    dep_l = (dep or "").lower()
    arr_l = (arr or "").lower()

    dep_in = dep_l in s
    arr_in = arr_l in s

    # Heuristic scoring
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


def resolve_sentence(sentence: str, mode: str = "baseline") -> ResolveResult:
    """
    UI/API wrapper around your existing resolver.

    mode:
      - "baseline": uses tor.nlp.parse_order (your rule-based + fuzzy)
      - "spacy": placeholder for later (kept to match UI toggle)
    """
    s = (sentence or "").strip()
    if not s:
        return ResolveResult(
            ok=False,
            confidence=0.0,
            debug={"reason": "empty_input", "mode": mode},
        )
    if mode == "baseline":
        try:
            from tor.nlp import parse_order  
        except Exception as e:
            return ResolveResult(
                ok=False,
                confidence=0.0,
                debug={
                    "reason": "import_error",
                    "mode": mode,
                    "details": repr(e),
                    "hint": "Check that src/tor exists and that Streamlit is run from project root.",
                    "src_dir": str(SRC_DIR),
                },
            )

        result = parse_order(s)

        if result is None:
            return ResolveResult(
                ok=False,
                confidence=0.15,
                debug={
                    "reason": "invalid_or_ambiguous",
                    "mode": mode,
                    "resolver": "tor.nlp.parse_order",
                },
            )

        dep, arr = result
        conf, conf_dbg = _basic_confidence(s, dep, arr)

        return ResolveResult(
            ok=True,
            departure=dep,
            arrival=arr,
            confidence=conf,
            debug={
                "mode": mode,
                "resolver": "tor.nlp.parse_order",
                **conf_dbg,
            },
        )
    if mode == "spacy":
        return ResolveResult(
            ok=False,
            confidence=0.0,
            debug={
                "reason": "spacy_mode_not_connected_yet",
                "mode": mode,
                "todo": "Plug spaCy STATION NER + disambiguation into resolver_service.resolve_sentence()",
            },
        )
    return ResolveResult(
        ok=False,
        confidence=0.0,
        debug={"reason": "unknown_mode", "mode": mode},
    )
