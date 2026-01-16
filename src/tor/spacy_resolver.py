from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List
import re

import spacy
from spacy.language import Language
from spacy.pipeline import EntityRuler


PROJECT_ROOT = Path(__file__).resolve().parents[2]  
CITIES_TXT = PROJECT_ROOT / "data" / "cities.txt"


def _normalize(txt: str) -> str:
    txt = (txt or "").lower().strip()
    txt = re.sub(r"[’']", " ", txt)
    txt = re.sub(r"[^a-zàâçéèêëîïôùûüÿñæœ0-9\s\-]", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _load_cities() -> List[str]:
    if not CITIES_TXT.exists():
        return []
    cities = []
    with open(CITIES_TXT, "r", encoding="utf-8") as f:
        for line in f:
            c = line.strip()
            if c and not c.startswith("#"):
                cities.append(c)
    return cities


_NLP: Optional[Language] = None


def _get_nlp() -> Language:
    """
    Build a lightweight spaCy pipeline:
    - blank French
    - EntityRuler with cities list
    Label: CITY
    """
    global _NLP
    if _NLP is not None:
        return _NLP

    nlp = spacy.blank("fr")
    ruler = nlp.add_pipe("entity_ruler")  

    cities = _load_cities()

    patterns = []
    for city in cities:
        city_norm = _normalize(city)
        if not city_norm:
            continue
        patterns.append({"label": "CITY", "pattern": city})

    ruler.add_patterns(patterns)
    _NLP = nlp
    return _NLP


def parse_order_spacy(sentence: str) -> Optional[Tuple[str, str]]:
    """
    NER-based resolver (simple + explainable):
    - Extract CITY entities with spaCy EntityRuler
    - Determine departure/arrival order using common French travel cues:
        * "de X à Y"
        * "depuis X vers Y"
        * "aller à Y" (incomplete -> None)
    Returns (departure_city, arrival_city) or None.
    """
    s = (sentence or "").strip()
    if not s:
        return None

    nlp = _get_nlp()
    doc = nlp(s)

    cities = [ent.text for ent in doc.ents if ent.label_ == "CITY"]
    seen = set()
    cities = [c for c in cities if not (c.lower() in seen or seen.add(c.lower()))]

    if len(cities) < 2:
        return None

    sent_norm = _normalize(s)

    # Try explicit "de X à Y" / "de X a Y"
    c1 = _normalize(cities[0])
    c2 = _normalize(cities[1])

    # Pattern: "de <city1> à <city2>" or "depuis <city1> vers <city2>"
    if f"de {c1} a {c2}" in sent_norm or f"de {c1} à {c2}" in sent_norm:
        return (cities[0], cities[1])
    if f"depuis {c1} vers {c2}" in sent_norm or f"depuis {c1} a {c2}" in sent_norm or f"depuis {c1} à {c2}" in sent_norm:
        return (cities[0], cities[1])

    # Fallback: assume order of first two extracted cities = dep -> arr
    return (cities[0], cities[1])
