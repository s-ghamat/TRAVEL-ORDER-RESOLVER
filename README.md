# Travel Order Resolver

NLP and SNCF data project for resolving French travel orders into train itineraries.

The system extracts departure and destination cities from natural language commands, validates the order, resolves stations and builds an itinerary using SNCF schedule data.

## Overview

Given an input such as:

```text
S42,Je voudrais aller de Paris à Lyon demain
```

The project produces:

```text
S42,Paris,Lyon
S42,SCHEDULE,DIRECT,Paris,Lyon,HH:MM:SS,HH:MM:SS,<trip_id>,<from_stop_name>,<to_stop_name>
```

The first line follows the strict project format.
The second line provides schedule proof using SNCF GTFS data.

## Scope

* French travel-order parsing
* Departure and destination extraction
* Valid and invalid order detection
* Station disambiguation with SNCF station data
* Schedule-based pathfinding with SNCF GTFS
* Direct route and one-transfer route search
* Optional Streamlit demo interface
* Synthetic dataset generation
* NLP benchmark pipeline

## Architecture

| Layer            | Purpose                                           |
| ---------------- | ------------------------------------------------- |
| NLP              | Extract origin and destination from text          |
| Station resolver | Match city names with SNCF stations               |
| Pathfinder       | Build routes from SNCF schedule data              |
| CLI              | Provide grading-friendly command-line tools       |
| API              | Expose unified resolver logic                     |
| UI               | Demonstrate the resolver with Streamlit           |
| Scripts          | Run pipelines, benchmarks, and dataset generation |

## Repository Structure

```text
src/
  tor/
    nlp.py
    spacy_resolver.py
    cli.py
    pathfinder_cli.py
    gtfs_pathfinder.py
    gtfs_pathfinder_cli.py

api/
  resolver_service.py
  stations.py
  pathfinder.py

data/
  sncf_clean/
    stations_clean.csv
  gtfs_sncf/
  synthetic/

ui/
  app.py

scripts/
  run_pipeline.sh
  run_pipeline_with_schedules.sh
  generate_synthetic_dataset.py
  benchmark_on_synthetic.py
```

## Requirements

* Python 3.10+
* macOS or Linux
* Virtual environment
* SNCF station data
* SNCF GTFS schedule data

## Installation

Create and activate a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install dependencies:

```sh
pip install -r requirements.txt
```

If `requirements.txt` is not available:

```sh
pip install pandas streamlit spacy rapidfuzz
```

## Data Setup

### Stations

The project expects the cleaned SNCF station file at:

```text
data/sncf_clean/stations_clean.csv
```

Required columns:

```text
station_name
uic_code
latitude
longitude
```

### GTFS Schedules

Download and unzip the SNCF GTFS theoretical timetable:

```sh
mkdir -p data/gtfs_sncf

curl -L "https://eu.ftp.opendatasoft.com/sncf/plandata/Export_OpenData_SNCF_GTFS_NewTripId.zip" \
  -o data/gtfs_sncf/sncf_gtfs.zip

unzip -o data/gtfs_sncf/sncf_gtfs.zip -d data/gtfs_sncf
```

Check the extracted files:

```sh
ls data/gtfs_sncf | head
```

Expected files include:

```text
stops.txt
stop_times.txt
trips.txt
routes.txt
```

## Usage

### NLP CLI

Input:

```text
sentenceID,sentence
```

Output:

```text
sentenceID,Departure,Destination
```

or:

```text
sentenceID,INVALID
```

Run:

```sh
PYTHONPATH=".:src" python -m tor.cli
```

Example:

```sh
echo "S1,Je voudrais aller de Paris à Lyon demain" | PYTHONPATH=".:src" python -m tor.cli
```

## Minimal Pathfinder

Input:

```text
sentenceID,Departure,Destination
```

Output:

```text
sentenceID,Departure,Step1,...,Destination
```

Run:

```sh
echo "S1,Paris,Lyon" | PYTHONPATH=".:src" python -m tor.pathfinder_cli
```

## End-to-End Pipeline

Run the NLP resolver followed by the minimal pathfinder:

```sh
./scripts/run_pipeline.sh < sentences.csv
```

Example:

```sh
echo "S1,Je voudrais aller de Paris à Lyon demain" | ./scripts/run_pipeline.sh
```

## Schedule-Based Pipeline

Run the full itinerary pipeline using SNCF GTFS schedules:

```sh
./scripts/run_pipeline_with_schedules.sh < sentences.csv
```

Example:

```sh
echo "S42,Je voudrais aller de Paris à Lyon demain" | ./scripts/run_pipeline_with_schedules.sh
```

Expected output:

```text
S42,Paris,Lyon
S42,SCHEDULE,DIRECT,Paris,Lyon,HH:MM:SS,HH:MM:SS,<trip_id>,<from_stop_name>,<to_stop_name>
```

For routes requiring one transfer:

```text
S42,Paris,<transfer>,Lyon
S42,SCHEDULE,1_TRANSFER,...
```

## Streamlit Demo

Run the optional UI:

```sh
source .venv/bin/activate
streamlit run ui/app.py
```

The interface displays:

* extracted travel order
* station candidates
* route proposal
* confidence score
* explanation timeline
* map view

## Synthetic Dataset

Generate a synthetic dataset:

```sh
source .venv/bin/activate
python scripts/generate_synthetic_dataset.py --n 10000 --invalid-ratio 0.25
```

Output:

```text
data/synthetic/synthetic_10k.csv
```

## Benchmark

Run the baseline benchmark:

```sh
PYTHONPATH=".:src" python scripts/benchmark_on_synthetic.py \
  --mode baseline \
  --in data/synthetic/synthetic_10k.csv
```

Run the spaCy benchmark:

```sh
PYTHONPATH=".:src" python scripts/benchmark_on_synthetic.py \
  --mode spacy \
  --in data/synthetic/synthetic_10k.csv
```

## Troubleshooting

### Missing `tor` module

Use:

```sh
PYTHONPATH=".:src" python -m tor.cli
```

### Missing `api` module

Use:

```sh
PYTHONPATH=".:src" python scripts/benchmark_on_synthetic.py
```

### Large GTFS files

`stop_times.txt` can be large. For faster experiments, use a subset of stops or add caching.

## Credits

* SNCF Open Data for station and GTFS schedule data
* spaCy for NLP components
* RapidFuzz for fuzzy matching
* Streamlit for the optional demo interface

## Author

Setayesh Ghamat
