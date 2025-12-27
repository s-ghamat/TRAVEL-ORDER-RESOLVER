import sys
from tor.nlp import parse_order

def main() -> int:
    for raw in sys.stdin:
        raw = raw.rstrip("\n")
        if not raw:
            continue

        if "," not in raw:
            print(f"{raw},INVALID_FORMAT")
            continue

        sentence_id, sentence = raw.split(",", 1)
        sentence_id = sentence_id.strip()
        sentence = sentence.strip()

        result = parse_order(sentence)

        if result is None:
            print(f"{sentence_id},INVALID")
        else:
            dep, dest = result
            print(f"{sentence_id},{dep},{dest}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
