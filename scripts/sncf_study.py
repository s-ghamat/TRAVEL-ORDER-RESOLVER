import pandas as pd
from pathlib import Path

def main():
    path = Path("data/sncf_raw/liste_des_gares.csv")
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        print("Put the downloaded CSV here and name it liste_des_gares.csv")
        return

    df = pd.read_csv(path, encoding="utf-8", sep=None, engine="python")

    print("=== SNCF Dataset Study ===")
    print(f"File: {path}")
    print(f"Rows: {len(df)}")
    print(f"Columns ({len(df.columns)}):")
    for c in df.columns:
        print(f"- {c}")

    print("\n=== Sample rows ===")
    print(df.head(5).to_string(index=False))

if __name__ == "__main__":
    main()
