import pandas as pd
from pathlib import Path

def split_coords(coord_str):
    if pd.isna(coord_str):
        return None, None
    try:
        lat, lon = coord_str.split(",")
        return float(lat.strip()), float(lon.strip())
    except Exception:
        return None, None

def normalize_col(col):
    """
    Remove BOM and strip spaces from column names.
    """
    return col.replace("\ufeff", "").strip()

def main():
    input_path = Path("data/sncf_raw/liste_des_gares.csv")
    output_path = Path("data/sncf_clean/stations_clean.csv")

    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        return

    df = pd.read_csv(input_path, encoding="utf-8", sep=None, engine="python")

    # Normalize column names (remove BOM + spaces)
    df.columns = [normalize_col(c) for c in df.columns]

    # Rename columns
    rename_map = {
        "Nom": "station_name",
        "Trigramme": "trigram",
        "Position géographique": "geo",
        "Code(s) UIC": "uic_code",
    }

    missing = [c for c in rename_map if c not in df.columns]
    if missing:
        print("ERROR: Missing expected columns:", missing)
        print("Found columns:", list(df.columns))
        return

    df = df.rename(columns=rename_map)

    # Split coordinates
    df[["latitude", "longitude"]] = df["geo"].apply(
        lambda x: pd.Series(split_coords(x))
    )

    # Keep useful columns only
    clean_df = df[[
        "station_name",
        "trigram",
        "uic_code",
        "latitude",
        "longitude",
    ]].copy()

    # Drop invalid rows
    clean_df = clean_df.dropna(subset=["station_name", "latitude", "longitude"])

    # Save cleaned dataset
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_path, index=False, encoding="utf-8")

    print("=== SNCF Clean Dataset Created ===")
    print(f"Rows: {len(clean_df)}")
    print(f"Saved to: {output_path}")
    print("\nSample rows:")
    print(clean_df.head(5).to_string(index=False))

if __name__ == "__main__":
    main()
