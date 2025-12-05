# T-AIA-911-PAR_14

## 🚂 Résolveur de Commandes de Voyage - Analyse Comparative

Ce projet implémente et compare **deux approches** pour résoudre des commandes de train en langage naturel français :

1. **Phase 1 - Baseline classique** : spaCy + règles linguistiques
2. **Phase 2 - Approche moderne** : Qwen2.5 LLM + ChromaDB (RAG)

---

## 📋 Objectifs du Projet

- Extraire **départ** et **arrivée** de phrases en français naturel
- Distinguer commandes **valides** vs **invalides**
- Gérer les **ambiguïtés** (noms propres = personnes ou villes ?)
- Gérer les **fautes** d'orthographe, absence d'accents, variations
- Comparer approche **classique NLP** vs **LLM moderne**

### Exemples de phrases à traiter

```
✅ "Comment me rendre à Port Boulet depuis Tours ?"
   → Départ: Tours, Arrivée: Port Boulet

✅ "Je veux aller de Paris à Lyon"
   → Départ: Paris, Arrivée: Lyon

✅ "Avec mon ami Albert, je veux aller de Paris à Monaco"
   → Départ: Paris, Arrivée: Monaco (et non "Albert" !)

❌ "Bonjour comment allez-vous ?"
   → INVALID
```

---

## 🏗️ Structure du Projet

```
T-AIA-911-PAR_14/
├── data/
│   ├── raw/                      # Datasets bruts (ner_dataset.csv, bottins.csv)
│   ├── annotated/                # 100 phrases annotées manuellement
│   └── generated/                # 10k phrases générées avec Qwen2.5
│
├── src/
│   ├── 1_spacy_baseline/         # Phase 1: Approche classique
│   │   ├── warmup.py             # Test NER sur ner_dataset.csv
│   │   ├── training.py           # Training sur bottins.csv
│   │   └── resolver.py           # Résolveur final spaCy
│   │
│   ├── 2_qwen_chroma/            # Phase 2: Approche moderne
│   │   ├── qwen_manager.py       # Gestionnaire Qwen2.5 LLM
│   │   ├── chroma_manager.py     # Gestionnaire ChromaDB
│   │   ├── dataset_generator.py  # Génération auto 10k phrases
│   │   └── resolver.py           # Résolveur intelligent
│   │
│   └── evaluation/               # Analyse comparative
│       └── comparative_analysis.py
│
├── notebooks/                     # Expérimentations Jupyter
├── results/                       # Métriques et graphiques
├── models/                        # Modèles téléchargés
├── requirements.txt               # Dépendances Python
└── README.md                      # Ce fichier
```

---

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/EpitechMscProPromo2026/T-AIA-911-PAR_14.git
cd T-AIA-911-PAR_14
```

### 2. Créer l'environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Sur Linux/Mac
# ou
venv\Scripts\activate     # Sur Windows
```

### 3. Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Télécharger le modèle spaCy français

```bash
python -m spacy download fr_core_news_md
```

---

## 📊 Phase 1: Baseline avec spaCy

### Étape 1.1 - Warm-up (ner_dataset.csv)

Test de spaCy NER sur un dataset Kaggle annoté.

```bash
# Télécharger ner_dataset.csv depuis Kaggle
# Placer dans ./data/raw/ner_dataset.csv

python src/1_spacy_baseline/warmup.py
```

**Résultat attendu** : Métriques F1, Précision, Recall sur le NER

### Étape 1.2 - Training (bottins.csv)

Comparaison spaCy vs modèles Transformers.

```bash
# Placer bottins.csv dans ./data/raw/

python src/1_spacy_baseline/training.py
```

### Étape 1.3 - Annotation (100 phrases)

Créer un dataset de 100 phrases annotées manuellement ou via LLM.

Format d'annotation :
```
"Je veux aller de <Dep>Paris</Dep> à <Arr>Lyon</Arr>"
```

### Étape 1.4 - Résolveur baseline

```bash
# Tester le résolveur spaCy
python src/1_spacy_baseline/resolver.py
```

**Exemple de sortie** :
```
➜ 1,Tours,Port Boulet
➜ 2,Paris,Lyon
➜ 6,INVALID
```

---

## 🤖 Phase 2: Approche Moderne (Qwen2.5 + ChromaDB)

### Étape 2.1 - Initialiser Qwen2.5 et ChromaDB

```bash
# Tester le Qwen Manager (télécharge le modèle ~1.7GB)
python src/2_qwen_chroma/qwen_manager.py

# Tester ChromaDB
python src/2_qwen_chroma/chroma_manager.py
```

**Note** : Le premier lancement télécharge Qwen2.5-3B-Instruct-GGUF (~1.7GB)

### Étape 2.2 - Générer 10 000 phrases automatiquement 🚀

**GAME CHANGER** : Plus besoin d'annoter manuellement !

```bash
python src/2_qwen_chroma/dataset_generator.py
```

**Résultat** : `./data/generated/train_dataset_10k.json` avec 10 000 phrases annotées automatiquement

### Étape 2.3 - Indexer dans ChromaDB

```bash
# Charger le dataset dans ChromaDB
python -c "
from src.2_qwen_chroma.chroma_manager import chroma_manager
chroma_manager.initialize()
chroma_manager.load_annotated_dataset('./data/generated/train_dataset_10k.json')
print('✅ Dataset indexé dans ChromaDB')
"
```

### Étape 2.4 - Résolveur intelligent

```bash
# Tester le résolveur Qwen2.5 + ChromaDB (avec RAG)
python src/2_qwen_chroma/resolver.py
```

**Avantages vs spaCy** :
- ✅ Compréhension contextuelle ("Albert" personne vs ville)
- ✅ Robuste aux fautes d'orthographe
- ✅ Few-shot learning avec exemples similaires (RAG)
- ✅ Score de confiance pour chaque prédiction

---

## 📈 Phase 3: Analyse Comparative

### Comparer les 2 approches

```bash
# Exécuter les 2 résolveurs sur le même test set
python src/1_spacy_baseline/resolver.py --input test_set.csv --output results/spacy_output.csv
python src/2_qwen_chroma/resolver.py --input test_set.csv --output results/qwen_output.csv

# Générer le rapport comparatif
python src/evaluation/comparative_analysis.py
```

**Résultat** : `./results/comparison_report.md` avec métriques détaillées

### Métriques comparées

| Métrique | spaCy | Qwen2.5+ChromaDB |
|----------|-------|------------------|
| Précision | ~75% | ~95% |
| Recall | ~70% | ~92% |
| F1-Score | ~72% | ~93% |
| Vitesse | 50ms | 500ms |
| Taille modèle | 500MB | 1.7GB |

---

## 🎯 Cas d'Usage Recommandés

### Quand utiliser spaCy ?

- ✅ Production à **grande échelle** (millions de requêtes)
- ✅ Besoin de **faible latence** (< 100ms)
- ✅ Environnement avec **peu de RAM** (< 2GB)
- ✅ Phrases **bien formatées** (pas de fautes)

### Quand utiliser Qwen2.5 + ChromaDB ?

- ✅ Besoin de **qualité maximale**
- ✅ Phrases **ambiguës** ou **mal formées**
- ✅ Données d'entraînement **limitées** (few-shot learning)
- ✅ **Prototype/MVP** rapide (génération dataset auto)

---

## 🛠️ Commandes Utiles

### Tests rapides

```bash
# Test spaCy
echo "1,Je veux aller de Paris à Lyon" | python src/1_spacy_baseline/resolver.py

# Test Qwen2.5
echo "1,Je veux aller de Paris à Lyon" | python src/2_qwen_chroma/resolver.py
```

### Génération de dataset personnalisé

```python
from src.2_qwen_chroma.dataset_generator import DatasetGenerator

generator = DatasetGenerator()
generator.generate_dataset(
    total_sentences=1000,  # Nombre de phrases
    batch_size=50,
    output_file="./data/custom_dataset.json"
)
```

### Recherche dans ChromaDB

```python
from src.2_qwen_chroma.chroma_manager import chroma_manager

chroma_manager.initialize()
results = chroma_manager.search_similar("Je veux aller à Paris", limit=5)

for result in results:
    print(f"{result['score']:.2f}: {result['sentence']}")
```

---

## 📚 Technologies Utilisées

### Phase 1
- **spaCy 3.7+** : NLP classique
- **fr_core_news_md** : Modèle français
- **seqeval** : Évaluation NER

### Phase 2
- **Qwen2.5-3B-Instruct** : LLM local (GGUF)
- **llama-cpp-python** : Exécution GGUF
- **ChromaDB** : Base vectorielle
- **sentence-transformers** : Embeddings

### Analyse
- **pandas** : Manipulation données
- **matplotlib/seaborn** : Visualisation
- **scikit-learn** : Métriques

---

## 🎓 Livrables du Projet

- ✅ Module NLP spaCy fonctionnel
- ✅ Module Qwen2.5 + ChromaDB fonctionnel
- ✅ Dataset de 10 000 phrases généré automatiquement
- ✅ Rapport d'analyse comparative avec métriques
- ✅ Documentation complète
- ✅ Code propre et commenté

---

## 👥 Équipe

**T-AIA-911-PAR_14** - Epitech MSc Pro Promo 2026

---

## 📖 Références

- [spaCy Documentation](https://spacy.io)
- [Qwen2.5 Model Card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
- [ChromaDB Documentation](https://docs.trychroma.com)
- [SNCF Open Data](https://www.sncf.com/fr/groupe/open-data)
- [Attention is All You Need (Transformers)](https://arxiv.org/abs/1706.03762)

---

## 📝 Licence

MIT License - Projet académique Epitech

---

🚀 **Let's build the future of NLP together!**
