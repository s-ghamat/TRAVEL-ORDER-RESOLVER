from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, Tuple

from api.resolver_service import resolve_sentence


def read_sentences(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        r = csv.reader(f)
        for row in r:
            if not row:
                continue
            if len(row) < 2:
                continue
            sid = row[0].strip()
            sent = row[1].strip()
            if sid and sent:
                yield sid, sent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=str, default="data/synthetic/synthetic_10k.csv")
    ap.add_argument("--mode", type=str, choices=["baseline", "spacy"], default="baseline")
    ap.add_argument("--helpful", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    path = Path(args.inp)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    n = 0
    n_ok = 0
    n_invalid = 0
    reasons = Counter()

    for sid, sent in read_sentences(path):
        n += 1
        res = resolve_sentence(sent, mode=args.mode, helpful=args.helpful)

        if res.ok:
            n_ok += 1
        else:
            n_invalid += 1
            reason = None
            if res.debug and "reason" in res.debug:
                reason = str(res.debug["reason"])
            reasons[reason or "unknown"] += 1

        if args.limit and n >= args.limit:
            break

    print("=== BENCHMARK ===")
    print("file:", str(path))
    print("mode:", args.mode)
    print("helpful:", bool(args.helpful))
    print("n:", n)
    print("ok:", n_ok, f"({(n_ok/n)*100:.1f}%)" if n else "")
    print("invalid:", n_invalid, f"({(n_invalid/n)*100:.1f}%)" if n else "")
    print("\nTop invalid reasons:")
    for k, v in reasons.most_common(10):
        print(f"- {k}: {v}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
