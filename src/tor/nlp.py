from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple, List

from unidecode import unidecode
from rapidfuzz import process, fuzz


# -----------------------------
# Normalization + city loading
# -----------------------------

def _norm(s: str) -> str:
    """
    Normalize a string for robust matching:
    - lowercase
    - remove accents
    - unify apostrophes
    - keep letters/numbers/spaces/hyphens/apostrophes
    - collapse whitespace
    """
    s = unidecode(s).lower()
    s = s.replace("’", "'")
    s = re.sub(r"[^a-z0-9\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _load_cities() -> List[str]:
    """
    Loads cities from data/cities.txt (one per line, UTF-8).
    Returns [] if file doesn't exist (so code still runs).
    """
    path = Path("data") / "cities.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


CITIES = _load_cities()
CITIES_NORM = {_norm(c): c for c in CITIES}  # normalized -> canonical


# -----------------------------
# Matching helper (Step 5.1)
# -----------------------------

def _best_city_match(fragment: str, score_cutoff: int = 85) -> Optional[str]:
    """
    Robust city matching with controlled typo tolerance.

    - Rejects very short fragments
    - Rejects ambiguity (multiple cities in one fragment)
    - Allows fuzzy matches with safety checks to avoid false positives
    """
    if not CITIES:
        return None

    frag_n = _norm(fragment)
    if not frag_n or len(frag_n) < 3:
        return None

    # Containment check (also detects ambiguity)
    contained = []
    for city_norm, city_can in CITIES_NORM.items():
        if city_norm and city_norm in frag_n:
            contained.append(city_can)

    if len(contained) > 1:
        return None
    if len(contained) == 1:
        return contained[0]

    # Fuzzy match against normalized city names
    choices = list(CITIES_NORM.keys())
    match = process.extractOne(
        frag_n,
        choices,
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff,
    )
    if not match:
        return None

    best_norm, _score, _idx = match

    # Safety: avoid matching very different-length strings
    if abs(len(best_norm) - len(frag_n)) > 4:
        return None

    return CITIES_NORM[best_norm]


# -----------------------------
# Rule-based patterns (Step 2)
# -----------------------------

_PATTERNS = [
    # "de X à Y"
    re.compile(r"\bde\s+(?P<dep>.+?)\s+(?:a|à)\s+(?P<dest>.+?)\b", re.IGNORECASE),
    # "depuis X à Y"
    re.compile(r"\bdepuis\s+(?P<dep>.+?)\s+(?:a|à)\s+(?P<dest>.+?)\b", re.IGNORECASE),
    # "de X vers Y"
    re.compile(r"\bde\s+(?P<dep>.+?)\s+vers\s+(?P<dest>.+?)\b", re.IGNORECASE),
    # "aller à Y depuis X"
    re.compile(
        r"\b(?:aller|vais|va|allons|allez)\s+(?:a|à)\s+(?P<dest>.+?)\s+depuis\s+(?P<dep>.+?)\b",
        re.IGNORECASE,
    ),
    # "me rendre à Y depuis X"
    re.compile(
        r"\b(?:me\s+rendre|rendre)\s+(?:a|à)\s+(?P<dest>.+?)\s+depuis\s+(?P<dep>.+?)\b",
        re.IGNORECASE,
    ),
]

# Step 3: travel keyword filter to quickly reject trash texts
TRAVEL_KEYWORDS = {
    "aller", "vais", "va", "allons", "allez",
    "rendre", "trajet", "voyage",
    "train", "bus", "avion",
    "de", "depuis", "vers", "a", "à",
}


def _clean_slot(text: str) -> str:
    """
    Cleanup a captured group (departure/destination chunk).
    Removes trailing punctuation and common polite/time words.
    """
    text = re.split(
        r"\b(?:aujourd|demain|ce\s+soir|svp|s'il\s+te\s+plait|s'il\s+vous\s+plait|merci)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = text.strip(" ,;:.!?")
    return text.strip()


# -----------------------------
# Main function used by CLI
# -----------------------------

def parse_order(sentence: str) -> Optional[Tuple[str, str]]:
    """
    Returns (departure, destination) as canonical city names when recognized.
    Returns None if invalid / incomplete / ambiguous.
    """
    s = sentence.strip()
    if not s or len(s) < 4:
        return None

    # Step 3: Quick reject for non-travel sentences (trash text)
    s_norm = _norm(s)
    if not any(k in s_norm.split() or k in s_norm for k in TRAVEL_KEYWORDS):
        return None

    # Try pattern-based extraction
    for pat in _PATTERNS:
        m = pat.search(s)
        if not m:
            continue

        dep_raw = _clean_slot(m.group("dep"))
        dest_raw = _clean_slot(m.group("dest"))

        dep = _best_city_match(dep_raw)
        dest = _best_city_match(dest_raw)

        # Reject incomplete
        if not dep or not dest:
            return None

        # Reject same-city travel
        if dep == dest:
            return None

        return dep, dest

    # If no pattern matched, it's incomplete/unsupported -> INVALID
    return None
