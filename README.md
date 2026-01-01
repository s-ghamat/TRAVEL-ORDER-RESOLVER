# Travel Order Resolver — NLP Module

This project implements a **rule-based NLP module** that extracts **departure** and **destination** cities from French travel requests.  
The system is designed to be **robust**, **safe**, and **easily evaluable** through a command-line interface.

---

## 📁 Project Structure

```

.
├── src/
│   └── tor/
│       ├── cli.py        # Command-line interface (stdin/stdout)
│       └── nlp.py        # NLP logic (normalization, parsing, matching)
├── data/
│   ├── cities.txt        # List of supported cities
│   ├── eval.csv          # Small labeled evaluation dataset
│   └── synthetic_eval.csv# Large synthetic evaluation dataset
├── scripts/
│   ├── evaluate.py       # Evaluation on eval.csv
│   ├── evaluate_file.py  # Evaluation on any CSV file
│   └── generate_dataset.py # Synthetic dataset generation
├── README.md
└── .venv/

````

---

## 🧠 NLP Overview

The NLP module:
- normalizes text (case, accents, punctuation)
- detects travel-related sentences
- extracts departure and destination using rule-based patterns
- handles mild misspellings with controlled fuzzy matching
- rejects ambiguous or incomplete requests

The system prioritizes **precision over recall** to avoid incorrect extractions.

---

## ⚙️ Setup

### 1) Create and activate virtual environment (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
````

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not present:

```bash
pip install pandas scikit-learn unidecode rapidfuzz
```

---

## ▶️ How to Run (CLI)

The program reads from **stdin** and writes to **stdout**.

### Example

```bash
PYTHONPATH=src python -m tor.cli << 'EOF'
1,Je souhaite me rendre à Paris depuis Toulouse
2,Bonjour comment ça va
EOF
```

### Output

```
1,Toulouse,Paris
2,INVALID
```

**Input format**

```
sentenceID,sentence
```

**Output format**

* `sentenceID,Departure,Destination`
* or `sentenceID,INVALID`

---

## 🧪 How to Test (Small Evaluation)

Run the predefined evaluation dataset:

```bash
python scripts/evaluate.py
```

This computes:

* Precision
* Recall
* F1-score

Example output:

```
TP=6 FP=0 FN=0 TN=6
Precision=1.000
Recall=1.000
F1=1.000
```

---

## 📊 Large-Scale Evaluation (Bonus)

### 1) Generate synthetic dataset

```bash
python scripts/generate_dataset.py
```

This creates:

```
data/synthetic_eval.csv
```

(500 automatically generated sentences: valid, invalid, ambiguous, noisy)

### 2) Evaluate on synthetic dataset

```bash
python scripts/evaluate_file.py data/synthetic_eval.csv
```

Example output:

```
Precision=0.921
Recall=0.812
F1=0.863
```

Error samples are printed to help analysis.

---

## 📈 Evaluation Metrics

* **Precision**: proportion of correct predictions among accepted sentences
* **Recall**: proportion of valid sentences correctly recognized
* **F1-score**: balance between precision and recall

The system is intentionally conservative to minimize false positives.

---

## ⚠️ Limitations

* Rule-based patterns may not cover all sentence structures
* Strong misspellings can lead to false negatives
* Some ambiguous constructions may be partially matched

These limitations are documented and analyzed in the project report.

---

## 🚀 Possible Improvements

* Extend pattern coverage
* Improve ambiguity detection
* Use machine learning or transformer-based NLP models

---

## ✅ Conclusion

This project provides:

* a clean CLI architecture
* a robust rule-based NLP solution
* controlled typo tolerance
* thorough evaluation with metrics
* clear error analysis

It is designed to be **easy to evaluate**, **safe**, and **academically rigorous**.