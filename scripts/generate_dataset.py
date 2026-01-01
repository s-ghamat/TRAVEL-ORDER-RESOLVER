import random
import csv
from pathlib import Path

from unidecode import unidecode

random.seed(42)

# Load cities from data/cities.txt
def load_cities():
    path = Path("data") / "cities.txt"
    cities = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return cities

CITIES = load_cities()

VALID_TEMPLATES = [
    "Je veux aller de {dep} à {dest}",
    "Je souhaite me rendre à {dest} depuis {dep}",
    "Je vais à {dest} depuis {dep}",
    "Je veux un trajet de {dep} vers {dest}",
    "Aller de {dep} à {dest} s'il vous plaît",
]

TRASH_TEXTS = [
    "Bonjour", "Salut", "Merci", "Comment ça va",
    "Quel temps fait-il", "Je m'appelle Paul",
    "Paris est une belle ville", "J'aime le train",
]

AMBIG_TEMPLATES = [
    "Je veux aller de {dep1} ou {dep2} à {dest}",
    "Je souhaite aller de {dep} à {dest1} ou {dest2}",
]

DEST_ONLY_TEMPLATES = [
    "Je veux aller à {dest}",
    "Aller à {dest} s'il te plaît",
]

DEP_ONLY_TEMPLATES = [
    "Je pars de {dep}",
    "Depuis {dep}",
]

def typo(city: str) -> str:
    """Create a mild typo: remove one character OR swap two adjacent characters."""
    c = unidecode(city)
    if len(c) < 4:
        return c
    mode = random.choice(["drop", "swap"])
    s = list(c)
    if mode == "drop":
        i = random.randrange(1, len(s) - 1)
        s.pop(i)
    else:
        i = random.randrange(1, len(s) - 2)
        s[i], s[i+1] = s[i+1], s[i]
    return "".join(s)

def make_valid(with_typos_prob=0.25):
    dep, dest = random.sample(CITIES, 2)
    tmpl = random.choice(VALID_TEMPLATES)
    if random.random() < with_typos_prob:
        dep_out = typo(dep) if random.random() < 0.5 else dep
        dest_out = typo(dest) if random.random() < 0.5 else dest
    else:
        dep_out, dest_out = dep, dest
    sent = tmpl.format(dep=dep_out, dest=dest_out)
    return sent, dep, dest, 1

def make_trash():
    sent = random.choice(TRASH_TEXTS)
    return sent, "", "", 0

def make_ambiguous():
    dep1, dep2, dest = random.sample(CITIES, 3)
    tmpl = random.choice(AMBIG_TEMPLATES)
    if "{dep1}" in tmpl:
        sent = tmpl.format(dep1=dep1, dep2=dep2, dest=dest)
    else:
        dest1, dest2, dep = random.sample(CITIES, 3)
        sent = tmpl.format(dep=dep, dest1=dest1, dest2=dest2)
    return sent, "", "", 0

def make_incomplete():
    if random.random() < 0.5:
        dest = random.choice(CITIES)
        sent = random.choice(DEST_ONLY_TEMPLATES).format(dest=dest)
    else:
        dep = random.choice(CITIES)
        sent = random.choice(DEP_ONLY_TEMPLATES).format(dep=dep)
    return sent, "", "", 0

def generate(n=500, out_path=Path("data") / "synthetic_eval.csv"):
    rows = []
    for i in range(1, n + 1):
        r = random.random()
        if r < 0.55:
            sent, dep, dest, v = make_valid()
        elif r < 0.75:
            sent, dep, dest, v = make_trash()
        elif r < 0.90:
            sent, dep, dest, v = make_incomplete()
        else:
            sent, dep, dest, v = make_ambiguous()

        rows.append({
            "sentence_id": str(i),
            "sentence": sent,
            "expected_dep": dep,
            "expected_dest": dest,
            "expected_valid": str(v),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sentence_id","sentence","expected_dep","expected_dest","expected_valid"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {n} rows to {out_path}")

if __name__ == "__main__":
    generate()
