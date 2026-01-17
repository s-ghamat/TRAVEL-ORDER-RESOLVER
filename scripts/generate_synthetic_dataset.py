from __future__ import annotations

import argparse
import csv
import random
import re
import unicodedata
from pathlib import Path
from typing import List, Tuple


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def random_case(s: str) -> str:
    mode = random.choice(["lower", "upper", "title", "mixed"])
    if mode == "lower":
        return s.lower()
    if mode == "upper":
        return s.upper()
    if mode == "title":
        return s.title()
    # mixed
    out = []
    for ch in s:
        out.append(ch.upper() if random.random() < 0.2 else ch.lower())
    return "".join(out)


def inject_typos(city: str) -> str:
    """
    Controlled simple typos: swap, drop, duplicate, replace a character.
    """
    if len(city) < 4 or random.random() > 0.35:
        return city

    s = city
    s_list = list(s)

    op = random.choice(["swap", "drop", "dup", "replace"])
    i = random.randint(1, len(s_list) - 2)

    if op == "swap" and i + 1 < len(s_list):
        s_list[i], s_list[i + 1] = s_list[i + 1], s_list[i]
    elif op == "drop":
        s_list.pop(i)
    elif op == "dup":
        s_list.insert(i, s_list[i])
    elif op == "replace":
        s_list[i] = random.choice(list("aeiouy"))
    return "".join(s_list)


def inject_noise(sentence: str) -> str:
    s = sentence

    # maybe remove accents globally
    if random.random() < 0.25:
        s = strip_accents(s)

    # maybe random casing
    if random.random() < 0.30:
        s = random_case(s)

    # maybe remove apostrophes 
    if random.random() < 0.20:
        s = s.replace("’", "'").replace("'", " ")

    if random.random() < 0.20:
        s = re.sub(r"\s+", " ", s).strip()
        s = " " * random.randint(0, 2) + s + " " * random.randint(0, 2)

    # punctuation noise
    if random.random() < 0.25:
        s = s + random.choice(["", ".", "!!", " ?", " ...", "!!!"])

    return s


def load_cities(cities_path: Path) -> List[str]:
    cities = []
    with open(cities_path, "r", encoding="utf-8") as f:
        for line in f:
            c = line.strip()
            if c and not c.startswith("#"):
                cities.append(c)
    return cities


def make_order_templates() -> List[str]:
    return [
        # classic patterns
        "Je voudrais aller de {A} à {B}",
        "Je veux aller de {A} à {B}",
        "Je souhaite me rendre à {B} depuis {A}",
        "Comment aller de {A} vers {B} ?",
        "Billet de {A} à {B}",
        "Un ticket {A} {B}",
        "Réserver un train de {A} à {B} pour demain",
        "Je pars de {A} et je vais à {B}",
        "Des trains en partance de {A} vers {B}",
        "Je voudrais un billet {A}-{B}",
        # with time words
        "Je veux aller de {A} à {B} demain",
        "Je veux aller de {A} à {B} ce soir",
        "Je veux aller de {A} à {B} lundi",
        # with extra context
        "Salut, je veux aller de {A} à {B} stp",
        "Je dois rejoindre {B} en partant de {A} avec mon ami Albert",
        "Pour le boulot: {A} -> {B}",
        # bonus: intermediate stop phrasing 
        "Je voudrais aller de {A} à {B} en passant par {C}",
        "Je veux aller de {A} à {B} via {C}",
    ]


def make_invalid_templates() -> List[str]:
    return [
        "Bonjour",
        "Merci beaucoup",
        "Je suis à la maison",
        "Quel temps fait-il à {A} ?",
        "J'aime {A}",
        "Avec mes amis florence et paris je mange une pizza",
        "Je veux aller demain",
        "Train",
        "Je veux un billet",
        "Peux-tu m'aider ?",
        "Je pars",
        "Aller à",
        "de à",
    ]


def sample_distinct(cities: List[str], k: int) -> List[str]:
    return random.sample(cities, k)


def generate_dataset(
    cities: List[str],
    n: int,
    invalid_ratio: float,
    seed: int,
) -> List[Tuple[str, str]]:
    random.seed(seed)

    order_templates = make_order_templates()
    invalid_templates = make_invalid_templates()

    rows: List[Tuple[str, str]] = []

    for i in range(1, n + 1):
        sid = f"S{i:05d}"

        if random.random() < invalid_ratio:
            t = random.choice(invalid_templates)
            A = random.choice(cities)
            s = t.format(A=A)
            s = inject_noise(s)
            rows.append((sid, s))
            continue

        # valid order
        A, B, C = sample_distinct(cities, 3)
        t = random.choice(order_templates)

        # apply typos sometimes to city names
        A2 = inject_typos(A)
        B2 = inject_typos(B)
        C2 = inject_typos(C)

        s = t.format(A=A2, B=B2, C=C2)
        s = inject_noise(s)
        rows.append((sid, s))

    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--invalid-ratio", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cities", type=str, default="data/cities.txt")
    ap.add_argument("--out", type=str, default="data/synthetic/synthetic_10k.csv")
    args = ap.parse_args()

    cities_path = Path(args.cities)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cities = load_cities(cities_path)
    if len(cities) < 5:
        raise SystemExit(f"Not enough cities in {cities_path} (got {len(cities)}). Need at least 5.")

    rows = generate_dataset(cities=cities, n=args.n, invalid_ratio=args.invalid_ratio, seed=args.seed)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for sid, sent in rows:
            w.writerow([sid, sent])

    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
