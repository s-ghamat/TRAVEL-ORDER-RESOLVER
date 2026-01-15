import sys
import pandas as pd
from pathlib import Path
import spacy
import re


def _variants(name: str) -> list[str]:
    """
    Generate simple text variants to improve matching:
    - hyphen to space
    - multiple spaces collapsed
    - normalize apostrophes
    """
    v = set()
    n = name.strip()
    v.add(n)

    n2 = n.replace("’", "'")
    v.add(n2)

    n3 = n2.replace("-", " ")
    v.add(" ".join(n3.split()))

    # also add the reverse: spaces to hyphen for common cases
    n4 = re.sub(r"\s+", "-", n2)
    v.add(n4)

    return [x for x in v if x]

def load_station_patterns(limit: int = 600):
    path = Path("data/sncf_clean/stations_clean.csv")
    if not path.exists():
        raise FileNotFoundError("data/sncf_clean/stations_clean.csv not found. Run scripts/sncf_clean.py first.")

    df = pd.read_csv(path, encoding="utf-8")
    names = df["station_name"].dropna().astype(str).unique().tolist()
    names = sorted(names, key=len, reverse=True)
    names = names[:limit]

    patterns = []
    for name in names:
        for v in _variants(name):
            patterns.append({"label": "STATION", "pattern": v})
    return patterns


def build_nlp():
    """
    Build a SpaCy pipeline that ONLY contains an EntityRuler (no pretrained NER),
    so the detected entities come only from our SNCF station patterns.
    """
    nlp = spacy.blank("fr") 

    ruler = nlp.add_pipe("entity_ruler", config={"phrase_matcher_attr": "LOWER"})
    ruler.add_patterns(load_station_patterns(limit=600))
    return nlp


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/spacy_ner_demo.py "your sentence here"')
        return

    text = sys.argv[1]
    nlp = build_nlp()
    doc = nlp(text)

    print("=== Input ===")
    print(text)
    print("\n=== Detected entities (EntityRuler only) ===")

    stations = [ent for ent in doc.ents if ent.label_ == "STATION"]
    if not stations:
        print("No STATION entities found.")
        return

    for ent in stations:
        print(f"- {ent.text} | label={ent.label_} | span=({ent.start_char},{ent.end_char})")


if __name__ == "__main__":
    main()
