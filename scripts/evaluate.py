import sys
import csv
from pathlib import Path

# Make src importable when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tor.nlp import parse_order


def safe_str(x):
    return "" if x is None else str(x)


def main():
    dataset_path = Path("data") / "eval.csv"
    if not dataset_path.exists():
        print("ERROR: data/eval.csv not found")
        return 1

    rows = []
    with dataset_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    tp = fp = fn = tn = 0
    errors = []

    for r in rows:
        sid = r["sentence_id"]
        sent = r["sentence"]
        exp_valid = int(r["expected_valid"])
        exp_dep = r["expected_dep"].strip() or None
        exp_dest = r["expected_dest"].strip() or None

        pred = parse_order(sent)
        pred_valid = 1 if pred is not None else 0

        if exp_valid == 1 and pred_valid == 1:
            # valid predicted valid: check exact match
            pred_dep, pred_dest = pred
            if pred_dep == exp_dep and pred_dest == exp_dest:
                tp += 1
            else:
                # wrong extraction counts as FP + FN in strict evaluation
                fp += 1
                fn += 1
                errors.append((sid, sent, "WRONG_PAIR", f"expected=({exp_dep},{exp_dest})", f"pred=({pred_dep},{pred_dest})"))
        elif exp_valid == 0 and pred_valid == 0:
            tn += 1
        elif exp_valid == 0 and pred_valid == 1:
            fp += 1
            pred_dep, pred_dest = pred
            errors.append((sid, sent, "FALSE_POSITIVE", "expected=INVALID", f"pred=({pred_dep},{pred_dest})"))
        elif exp_valid == 1 and pred_valid == 0:
            fn += 1
            errors.append((sid, sent, "FALSE_NEGATIVE", f"expected=({exp_dep},{exp_dest})", "pred=INVALID"))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    print("=== Evaluation Results ===")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Precision={precision:.3f}")
    print(f"Recall={recall:.3f}")
    print(f"F1={f1:.3f}")

    if errors:
        print("\n=== Errors (up to 20) ===")
        for e in errors[:20]:
            sid, sent, etype, exp, pred = e
            print(f"- id={sid} | {etype}")
            print(f"  sentence: {sent}")
            print(f"  {exp}")
            print(f"  {pred}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
