from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple, List

from unidecode import unidecode
from rapidfuzz import process, fuzz


# ---- City loading + normalization ----

def _norm(s: str) -> str:
    """
    Normalization for robust matching:
    - lowercase
    - remove accents
    - keep letters/numbers/spaces/hyphens
    - collapse whitespace
    """
    s = unidecode(s).lower()
    s = s.replace("’", "'")
    s = re.sub(r"[^a-z0-9\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _load_cities() -> List[str]:
    # data/cities.txt relative to repo root (works when running from repo)
    path = Path("data") / "cities.txt"
    if not path.exists():
        return []
    cities = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return cities


CITIES = _load_cities()
CITIES_NORM = {_norm(c): c for c in CITIES}  # normalized -> canonical


def _best_city_match(fragment: str, score_cutoff: int = 90) -> Optional[str]:
    """
    Fuzzy match a fragment to a city. Returns canonical city name or None.
    """
    if not CITIES:
        return None

    frag_n = _norm(fragment)

    # Exact / near-exact match on normalized strings
    if frag_n in CITIES_NORM:
        return CITIES_NORM[frag_n]

    # Fuzzy match: compares fragment to normalized city names
    choices = list(CITIES_NORM.keys())
    match = process.extractOne(
        frag_n,
        choices,
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff,
    )
    if not match:
        return None

    best_norm, score, _idx = match
    return CITIES_NORM[best_norm]


# ---- Pattern-based parsing ----

# We keep patterns simple first, then add more later.
_PATTERNS = [
    # "de X à Y"
    re.compile(r"\bde\s+(?P<dep>.+?)\s+(?:a|à)\s+(?P<dest>.+?)\b", re.IGNORECASE),
    # "depuis X à Y"
    re.compile(r"\bdepuis\s+(?P<dep>.+?)\s+(?:a|à)\s+(?P<dest>.+?)\b", re.IGNORECASE),
    # "de X vers Y"
    re.compile(r"\bde\s+(?P<dep>.+?)\s+vers\s+(?P<dest>.+?)\b", re.IGNORECASE),
    # "aller à Y depuis X"
    re.compile(r"\b(?:aller|vais|va|allons|allez)\s+(?:a|à)\s+(?P<dest>.+?)\s+depuis\s+(?P<dep>.+?)\b", re.IGNORECASE),
    # "me rendre à Y depuis X"
    re.compile(r"\b(?:me\s+rendre|rendre)\s+(?:a|à)\s+(?P<dest>.+?)\s+depuis\s+(?P<dep>.+?)\b", re.IGNORECASE),
]


def _clean_slot(text: str) -> str:
    # Stop at common trailing words that are not part of city name
    text = re.split(r"\b(?:aujourd|demain|ce\s+soir|svp|s'il\s+te\s+plait|merci)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = text.strip(" ,;:.!?")
    return text.strip()


def parse_order(sentence: str) -> Optional[Tuple[str, str]]:
    """
    Return (departure, destination) in canonical city names if recognized.
    Else return None -> INVALID.
    """
    s = sentence.strip()
    if not s:
        return None

    # Quick reject: too short
    if len(s) < 4:
        return None

    for pat in _PATTERNS:
        m = pat.search(s)
        if not m:
            continue

        dep_raw = _clean_slot(m.group("dep"))
        dest_raw = _clean_slot(m.group("dest"))

        dep = _best_city_match(dep_raw)
        dest = _best_city_match(dest_raw)

        if dep and dest and dep != dest:
            return dep, dest

    return None
