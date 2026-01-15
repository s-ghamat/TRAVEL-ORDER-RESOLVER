import sys
import pandas as pd
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/station_search.py <query> [k]")
        print('Example: python scripts/station_search.py "paris" 10')
        return

    query = sys.argv[1].strip().lower()
    k = int(sys.argv[2]) if len(sys.argv) >= 3 else 10

    path = Path("data/sncf_clean/stations_clean.csv")
    if not path.exists():
        print(f"ERROR: {path} not found. Run scripts/sncf_clean.py first.")
        return

    df = pd.read_csv(path, encoding="utf-8")
    mask = df["station_name"].astype(str).str.lower().str.contains(query, na=False)
    hits = df[mask].head(k)

    print(f"=== Station search: '{query}' (top {k}) ===")
    if hits.empty:
        print("No matches.")
        return

    print(hits.to_string(index=False))

if __name__ == "__main__":
    main()
