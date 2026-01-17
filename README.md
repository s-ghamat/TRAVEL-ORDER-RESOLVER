# TRAVEL ORDER RESOLVER (NLP + SNCF)

NLP + data project: resolve French travel orders (departure/destination) and generate an itinerary using SNCF data.

This repository contains:

* an isolated **NLP module** (baseline rule-based + spaCy NER approach)
* a **station disambiguation layer** using SNCF “Gares de voyageurs”
* a **schedule-based pathfinder** using SNCF **GTFS** theoretical timetables
* (optional demo) a Streamlit UI

---

## 1) Project goals

Given text commands like:

* `S42,Je voudrais aller de Paris à Lyon demain`

The system:

1. extracts origin/destination (city-level)
2. distinguishes valid vs invalid orders
3. finds a route using SNCF schedules (GTFS)
4. outputs:

   * a strict **route line** (spec format)
   * a second line with **schedule proof** (times + trip_id)

---

## 2) Repository structure (high-level)

* `src/tor/`

  * `nlp.py` : baseline rule-based parser (regex + normalization + fuzzy matching)
  * `spacy_resolver.py` : spaCy EntityRuler approach (cities NER)
  * `cli.py` : NLP CLI (stdin: `sentenceID,sentence`)
  * `pathfinder_cli.py` : minimal spec pathfinder (triplet -> route)
  * `gtfs_pathfinder.py` : schedule engine (GTFS direct + 1-transfer)
  * `gtfs_pathfinder_cli.py` : schedule pathfinder CLI (triplet -> route + schedule line)
* `api/`

  * `resolver_service.py` : unified resolver with confidence + helpful fallback
  * `stations.py` : SNCF station search + candidates
  * `pathfinder.py` : simple itinerary builder for the UI layer (stations + distances)
* `data/`

  * `sncf_clean/stations_clean.csv` : cleaned SNCF stations (name, UIC, lat/lon)
  * `gtfs_sncf/` : SNCF GTFS files (stops.txt, stop_times.txt, trips.txt…)
  * `synthetic/` : generated synthetic datasets
* `ui/`

  * `app.py` : Streamlit demo UI
* `scripts/`

  * `run_pipeline.sh` : NLP -> minimal pathfinder
  * `run_pipeline_with_schedules.sh` : NLP -> GTFS schedule pathfinder
  * `generate_synthetic_dataset.py` : synthetic dataset generator
  * `benchmark_on_synthetic.py` : benchmark runner (OK vs INVALID)

---

## 3) Requirements

* macOS / Linux
* Python 3.10+ recommended
* A virtual environment (required)

---

## 4) Setup

### 4.1 Create & activate venv

From project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 4.2 Install dependencies

If you have `requirements.txt`:

```bash
pip install -r requirements.txt
```

If not, install the minimal set:

```bash
pip install pandas streamlit spacy rapidfuzz
```

(If you use additional packages, add them to `requirements.txt`.)

---

## 5) Data setup

### 5.1 SNCF stations (already cleaned in this project)

This project expects:

```
data/sncf_clean/stations_clean.csv
```

Columns:

* `station_name`
* `uic_code`
* `latitude`
* `longitude`

### 5.2 SNCF GTFS schedules (required to satisfy “using SNCF schedules”)

Download + unzip:

```bash
mkdir -p data/gtfs_sncf
curl -L "https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip" \
  -o data/gtfs_sncf/sncf_gtfs.zip
unzip -o data/gtfs_sncf/sncf_gtfs.zip -d data/gtfs_sncf
```

Sanity check:

```bash
ls data/gtfs_sncf | head
```

You should see: `stops.txt`, `stop_times.txt`, `trips.txt`, `routes.txt`, etc.

---

## 6) How to run (grading-friendly)

### 6.1 NLP CLI only (spec format)

Input: `sentenceID,sentence`
Output: `sentenceID,Departure,Destination` or `sentenceID,INVALID`

```bash
source .venv/bin/activate
PYTHONPATH=".:src" python -m tor.cli
```

Example:

```bash
echo "S1,Je voudrais aller de Paris à Lyon demain" | PYTHONPATH=".:src" python -m tor.cli
```

### 6.2 Minimal pathfinder CLI (spec format)

Input: `sentenceID,Departure,Destination`
Output: `sentenceID,Departure,Step1,...,Destination`

```bash
echo "S1,Paris,Lyon" | PYTHONPATH=".:src" python -m tor.pathfinder_cli
```

### 6.3 End-to-end pipeline (NLP -> minimal pathfinder)

```bash
./scripts/run_pipeline.sh < sentences.csv
```

Test:

```bash
echo "S1,Je voudrais aller de Paris à Lyon demain" | ./scripts/run_pipeline.sh
```

### 6.4 End-to-end pipeline WITH SNCF schedules (recommended)

This is the final “real itinerary” pipeline using GTFS schedules.

```bash
./scripts/run_pipeline_with_schedules.sh < sentences.csv
```

Test:

```bash
echo "S42,Je voudrais aller de Paris à Lyon demain" | ./scripts/run_pipeline_with_schedules.sh
```

Expected output: **two lines**

1. strict route line (spec):

* `S42,Paris,Lyon`

2. schedule proof line:

* `S42,SCHEDULE,DIRECT,Paris,Lyon,HH:MM:SS,HH:MM:SS,<trip_id>,<from_stop_name>,<to_stop_name>`

If the route requires a transfer, you may see:

* `S42,Paris,<transfer>,Lyon`
* `S42,SCHEDULE,1_TRANSFER,...`

---

## 7) Streamlit demo UI (optional)

```bash
source .venv/bin/activate
streamlit run ui/app.py
```

The UI shows:

* resolution steps (NLP -> station disambiguation -> route)
* a confidence score + explainability timeline
* a map

---

## 8) Synthetic dataset generation + benchmark

### 8.1 Generate a 10k dataset (sentenceID,sentence)

```bash
source .venv/bin/activate
python scripts/generate_synthetic_dataset.py --n 10000 --invalid-ratio 0.25
```

Outputs:

* `data/synthetic/synthetic_10k.csv`

### 8.2 Benchmark “OK vs INVALID” rate

Because `api/` is at project root and `tor/` is under `src/`, use:

```bash
PYTHONPATH=".:src" python scripts/benchmark_on_synthetic.py --mode baseline --in data/synthetic/synthetic_10k.csv
PYTHONPATH=".:src" python scripts/benchmark_on_synthetic.py --mode spacy --in data/synthetic/synthetic_10k.csv
```

---

## 9) Notes / troubleshooting

### “ModuleNotFoundError: No module named 'tor'”

Run with:

```bash
PYTHONPATH=".:src" python -m tor.cli
```

### “ModuleNotFoundError: No module named 'api'”

Same fix:

```bash
PYTHONPATH=".:src" python scripts/benchmark_on_synthetic.py ...
```

### Performance

GTFS `stop_times.txt` can be large. For faster experiments:

* limit to a subset of stops/trips, or
* add caching (future improvement)

---

## 10) License / Credits

* SNCF Open Data (stations + GTFS schedules)
* spaCy (French pipeline + EntityRuler)
