# Documentation du processus - Travel Order Resolver

Ce document retrace les étapes de développement du projet Travel Order Resolver. J'ai documenté au fur et à mesure ce que j'ai fait, les choix techniques que j'ai pris, et les résultats obtenus.

## Étape 1 : Récupération des données SNCF

### Objectif
J'avais besoin de la liste complète des villes et gares SNCF pour générer des phrases réalistes dans le dataset. J'ai donc récupéré ces données depuis l'API Open Data SNCF.

### Implémentation

#### Script principal : `scripts/01_fetch_sncf_data.py`

J'ai créé ce script pour télécharger toutes les données SNCF. Voici ce qu'il fait :

1. **Téléchargement des données**
   - J'utilise l'API SNCF Open Data : `https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/gares-de-voyageurs/records`
   - J'ai dû gérer la pagination car l'API renvoie 100 enregistrements par page
   - Au final, j'ai récupéré 2785 gares
   - Les données brutes sont sauvegardées dans `data/sncf/gares_raw.json`

2. **Analyse de la structure**
   - J'ai d'abord analysé la structure JSON pour comprendre ce que je recevais
   - Les colonnes disponibles sont : nom, libellecourt, segment_drg, position_geographique, codeinsee, codes_uic
   - J'affiche quelques exemples de gares pour vérifier que tout est correct

3. **Extraction des villes et gares**
   - J'extrais le nom de chaque gare depuis le champ "nom"
   - Pour obtenir le nom de la ville, j'ai créé une fonction `extract_city_from_station_name` qui gère les cas comme "Paris-Nord" -> "Paris"
   - Je normalise les noms de villes (capitalisation, gestion des tirets) pour éviter les doublons
   - Après déduplication, j'obtiens la liste des villes uniques
   - J'ai aussi identifié quelques villes potentiellement ambiguës (prénoms communs : Albert, Lourdes, Pierre, Valence) pour les gérer plus tard

4. **Sauvegarde des données traitées**
   - `data/sncf/gares_raw.json` : Données brutes de l'API (2785 gares)
   - `data/sncf/villes_list.json` : Liste des 2567 villes uniques (format JSON array)
   - `data/sncf/gares_list.json` : Liste détaillée des gares avec mapping ville/gare (format JSON array d'objets)
   - `data/sncf/villes_ambiguës.json` : Liste des 4 villes ambiguës identifiées

### Résultats

Au final, j'ai récupéré :
- **2785 gares** téléchargées et traitées
- **2567 villes uniques** extraites et normalisées
- **4 villes ambiguës** identifiées (Albert, Lourdes, Pierre, Valence)
- Toutes les villes majeures sont présentes (Paris, Lyon, Marseille, Toulouse, Bordeaux, Nantes, etc.)
- Les codes UIC et INSEE sont présents pour toutes les gares, ce qui sera utile pour le pathfinder plus tard

### Structure des données

#### Format `gares_raw.json`
```json
{
  "total_count": 2785,
  "records": [
    {
      "nom": "Montsûrs",
      "libellecourt": "MSW",
      "segment_drg": "C",
      "position_geographique": {
        "lon": -0.5506416,
        "lat": 48.14149
      },
      "codeinsee": "53043",
      "codes_uic": "87478537"
    }
  ]
}
```

#### Format `villes_list.json`
```json
[
  "Abancourt",
  "Abbaretz",
  "Abbeville",
  ...
]
```

#### Format `gares_list.json`
```json
[
  {
    "nom_gare": "Montsûrs",
    "ville": "Montsûrs",
    "nom_simple": "Montsûrs",
    "code_uic": "87478537",
    "codeinsee": "53043"
  }
]
```

### Fonctions utilitaires

- `normalize_city_name(city)` : Normalise le nom d'une ville (capitalisation, gestion des tirets)
- `extract_simple_name(full_name)` : Extrait un nom simplifié depuis le nom complet de la gare
- `extract_city_from_station_name(station_name)` : Extrait le nom de la ville depuis le nom de la gare (gère les cas comme "Paris-Nord" -> "Paris", "Pont de Lignon" -> "Lignon")

### Script d'analyse optionnel

Le script `scripts/01_analyze_sncf_structure.py` permet d'afficher des statistiques sur les données téléchargées :
- Nombre total de gares et villes
- Liste des villes ambiguës
- Exemples de villes majeures avec leurs variantes
- Statistiques sur les codes UIC et INSEE

---

## Étape 2 : Génération du dataset

### Objectif
Je devais générer un dataset de 10 000 phrases annotées pour entraîner le modèle NER. J'ai aussi besoin d'exporter dans différents formats : JSONL pour BERT et CSV pour validation humaine.

**Note** : J'ai d'abord créé un draft de 100 phrases pour tester que tout le pipeline fonctionnait, puis j'ai généré le dataset complet de 10 000 phrases.

### Implémentation

#### Fichier de templates : `data/templates/sentence_templates.json`

J'ai créé un fichier avec plus de 200 templates uniques, organisés en catégories pour couvrir différents cas :

- **Valides - Formes directes** : ~30 templates avec variations (je voudrais, j'aimerais, je souhaite, etc.)
- **Valides - Formes interrogatives** : ~20 templates (Comment, Y a-t-il, Quels sont les horaires, etc.)
- **Valides - Avec contexte** : ~20 templates (pour un rendez-vous, pour les vacances, pour voir un ami, etc.)
- **Valides - Ordre inversé** : ~15 templates (depuis X je veux aller à Y, etc.)
- **Invalides - Sans origine** : ~15 templates (Je voudrais aller à Y, etc.)
- **Invalides - Sans destination** : ~15 templates (Je voudrais partir de X, etc.)
- **Invalides - Phrases non liées** : ~20 phrases (Bonjour, Quel temps fait-il, etc.)
- **Ambiguïtés - Prénoms** : ~15 templates (Je veux aller voir mon ami Albert, etc.)
- **Ambiguïtés - Mots communs** : ~15 templates (Port-Boulet, gare de X, etc.)

Chaque template a au moins 3-5 variations, ce qui me donne plus de 500 variantes possibles au total. C'est important pour avoir de la diversité dans le dataset.

#### Script 1 : `scripts/02_generate_dataset_draft.py`

Ce script génère les phrases brutes. Voici ce qu'il fait :

1. **Chargement des données**
   - Je charge les templates depuis `data/templates/sentence_templates.json`
   - Je charge la liste des villes depuis `data/sncf/villes_list.json`
   - Je charge aussi les villes ambiguës depuis `data/sncf/villes_ambiguës.json` pour les utiliser dans les cas d'ambiguïté

2. **Génération des phrases**
   - Je génère 70 phrases valides (avec origine + destination)
   - 20 phrases invalides (sans origine ou sans destination)
   - 10 phrases avec ambiguïtés (prénoms, mots communs) pour tester la robustesse
   - Toutes les phrases utilisent des villes réelles de la liste SNCF que j'ai récupérée

3. **Application de variations**
   - J'applique des variations de casse (majuscules/minuscules/mixte) pour rendre le dataset plus réaliste
   - Je gère aussi les variations de tirets (Saint-Denis vs saint denis)
   - J'ajoute quelques fautes d'orthographe légères (suppression de lettres) pour tester la robustesse

4. **Sauvegarde**
   - Sauvegarde les phrases brutes dans `data/dataset/draft/sentences_raw.txt`
   - Format : `id,phrase`

#### Script 2 : `scripts/03_annotate_dataset.py`

**Fonctionnalités :**

1. **Extraction origine/destination**
   - Charge les phrases générées
   - Pour chaque phrase, identifie l'origine et la destination
   - Utilise des patterns regex pour détecter :
     * "de X à Y" / "depuis X vers Y"
     * Ordre inversé "à Y depuis X"
     * Deux villes consécutives "X Y"
   - Normalise les noms de villes (insensible à la casse, tirets, accents)

2. **Calcul des positions**
   - Trouve les positions exactes (start, end) de chaque ville dans le texte
   - Gère les variations de casse et de formatage

3. **Création des annotations**
   - Format JSON avec :
     * id : identifiant de la phrase
     * text : texte de la phrase
     * entities : liste des entités trouvées (ORIGIN, DESTINATION) avec positions
     * is_valid : booléen indiquant si la phrase est valide
     * origin : nom de la ville d'origine (normalisé)
     * destination : nom de la ville de destination (normalisé)

4. **Sauvegarde**
   - Sauvegarde dans `data/dataset/draft/annotations.json`

#### Script 3 : `scripts/04_export_formats.py`

**Fonctionnalités :**

1. **Split train/validation**
   - Charge les annotations
   - Split 80/20 (train/validation)
   - Mélange aléatoire avant le split

2. **Export JSONL (format BERT)**
   - `data/dataset/draft/train.jsonl` : 80 phrases
   - `data/dataset/draft/validation.jsonl` : 20 phrases
   - Format : une ligne JSON par phrase (compatible avec l'entraînement BERT/NER)

3. **Export CSV (format lisible)**
   - `data/dataset/draft/train.csv` : phrases (id, text)
   - `data/dataset/draft/train_labels.csv` : labels (id, origin, destination, is_valid)
   - `data/dataset/draft/validation.csv` : phrases
   - `data/dataset/draft/validation_labels.csv` : labels

### Résultats

**Dataset complet (10 000 phrases) :**
- **10 000 phrases générées** avec annotations complètes
- **8 000 phrases d'entraînement** (5 532 valides, 2 468 invalides)
- **2 000 phrases de validation** (1 324 valides, 676 invalides)
- **Répartition** : 70% valides, 20% invalides, 10% ambiguïtés
- **Formats exportés** : JSONL (BERT) et CSV (validation humaine)
- **Toutes les phrases utilisent des villes réelles** de la liste SNCF

**Dataset draft (100 phrases) :**
- Un premier draft de 100 phrases a été créé pour tester le pipeline
- Conservé dans `data/dataset/draft/` pour référence

### Structure des fichiers de sortie

#### Format JSONL (`train.jsonl`, `validation.jsonl`)
```json
{"id": 1, "text": "je voudrais aller de Toulouse à bordeaux", "entities": [{"text": "Toulouse", "label": "ORIGIN", "start": 20, "end": 28}, {"text": "bordeaux", "label": "DESTINATION", "start": 31, "end": 39}], "is_valid": true, "origin": "Toulouse", "destination": "Bordeaux"}
```

#### Format CSV (`train.csv`)
```csv
id,text
1,"je voudrais aller de Toulouse à bordeaux"
```

#### Format CSV Labels (`train_labels.csv`)
```csv
id,origin,destination,is_valid
1,Toulouse,Bordeaux,true
```

### Utilisation

**Pour générer le dataset complet (10 000 phrases) :**

```bash
python scripts/02_generate_full_dataset.py
python scripts/03_annotate_full_dataset.py
python scripts/04_export_full_dataset.py
```

**Pour générer le dataset draft (100 phrases) :**

```bash
python scripts/02_generate_dataset_draft.py
python scripts/03_annotate_dataset.py
python scripts/04_export_formats.py
```

**Fichiers du dataset complet** (dans `data/dataset/full/`) :
- `train.jsonl` (8 000 phrases) et `validation.jsonl` (2 000 phrases) pour l'entraînement BERT
- `train.csv`, `train_labels.csv`, `validation.csv`, `validation_labels.csv` pour validation humaine
- `sentences_raw.txt` : phrases brutes générées
- `annotations.json` : annotations complètes

**Fichiers du dataset draft** (dans `data/dataset/draft/`) :
- Conservés pour référence et tests rapides

---

## Étape 3 : Baseline basée sur les prépositions et évaluation

### Objectif
Implémenter une baseline simple basée sur les prépositions pour extraire origine et destination, l'évaluer sur le dataset de validation, et calculer les métriques de performance.

### Implémentation

#### Modèle baseline : `models/baseline/baseline_model.py`

**Fonctionnalités principales :**

- Classe `BaselineModel` qui implémente l'extraction basée sur les prépositions
- Détecte les prépositions d'origine : "de", "depuis", "à partir de", "en partant de"
- Détecte les prépositions de destination : "à", "vers", "jusqu'à", "pour aller à"
- Extrait le nom de ville après chaque préposition
- Normalise les noms de villes (casse, tirets, accents) pour la correspondance
- Gère les cas sans préposition (recherche de deux villes consécutives)
- Retourne le format attendu : `(sentence_id, origin, destination)` ou `(sentence_id, "INVALID", "")`

**Logique d'extraction :**

1. Cherche les prépositions d'origine et de destination dans le texte
2. Extrait le segment de texte après chaque préposition (jusqu'à 3-4 mots)
3. Cherche une ville dans ce segment en normalisant et comparant avec la liste des villes SNCF
4. Si aucune préposition n'est trouvée, cherche deux villes consécutives dans le texte
5. Détermine si la phrase est valide (origine ET destination présentes)

#### Script d'évaluation : `scripts/05_evaluate_baseline.py`

**Fonctionnalités :**

- Charge le dataset de validation (`validation.jsonl` et `validation_labels.csv`)
- Applique la baseline sur chaque phrase
- Compare les prédictions avec les labels réels
- Calcule les métriques :
  * **Pour ORIGIN** : Precision, Recall, F1-score
  * **Pour DESTINATION** : Precision, Recall, F1-score
  * **Pour phrases valides/invalides** : Taux de détection correcte
  * **Métriques globales** : Exact match (les deux villes correctes)
- Sauvegarde les résultats dans `evaluation/results/baseline_results.json`

#### Utilitaires de métriques : `evaluation/metrics.py`

Fonctions pour calculer :
- `calculate_metrics_for_label()` : Precision, Recall, F1 pour un label
- `calculate_exact_match()` : Taux de correspondance exacte
- `calculate_valid_invalid_detection()` : Taux de détection des phrases valides/invalides

### Résultats de l'évaluation

J'ai testé sur le dataset de validation (20 phrases du draft) :

**Métriques pour ORIGIN :**
- Precision : 0.7857 (78.57%)
- Recall : 0.6471 (64.71%)
- F1-score : 0.7097 (70.97%)
- TP: 11, FP: 3, FN: 6

**Métriques pour DESTINATION :**
- Precision : 0.9286 (92.86%)
- Recall : 0.8125 (81.25%)
- F1-score : 0.8667 (86.67%)
- TP: 13, FP: 1, FN: 3

**Métriques globales :**
- Exact match rate : 0.7000 (70% des phrases valides ont origine ET destination correctes)
- Valid detection rate : 0.8750 (87.5% des phrases valides sont correctement identifiées)
- Invalid detection rate : 1.0000 (100% des phrases invalides sont correctement identifiées)

### Analyse des résultats

Pour une approche simple basée sur les prépositions, les résultats sont corrects mais perfectibles :
- La destination est mieux détectée que l'origine (F1 de 86.67% vs 70.97%), probablement parce que "à" est plus fréquent et clair que "de"
- La précision est élevée pour la destination (92.86%), donc peu de faux positifs
- La détection des phrases invalides fonctionne parfaitement (100%)
- L'exact match à 70% montre que la baseline trouve les deux villes dans la majorité des cas, mais il y a encore de la marge d'amélioration

**Limites que j'ai identifiées :**
- Difficulté à gérer les cas avec variations de casse importantes
- Problèmes avec les villes composées (ex: "Port-Boulet")
- Difficulté à distinguer prénoms et villes (ex: "Albert")
- Le recall plus faible pour l'origine (64.71%) indique que certaines origines sont manquées, probablement à cause de prépositions moins évidentes

### Utilisation

Pour tester la baseline :
```bash
python scripts/06_test_baseline.py
```

Pour évaluer sur le dataset de validation :
```bash
python scripts/05_evaluate_baseline.py
```

Les résultats sont sauvegardés dans `evaluation/results/baseline_results.json`.

---

## Exploration spaCy NER (bonus - non complété)

### Objectif
Explorer l'utilisation de spaCy NER (modèle pré-entraîné) pour détecter les villes dans les phrases et comparer avec la baseline.

### Problème rencontré

J'ai essayé d'utiliser spaCy mais j'ai rencontré un problème de compatibilité avec Python 3.14. spaCy 3.8.11 n'est pas compatible à cause d'un problème dans pydantic v1. Le modèle ne peut pas être chargé.

**Message d'erreur que j'ai eu** :
```
pydantic.v1.errors.ConfigError: unable to infer type for attribute "REGEX"
```

### Script créé

J'ai quand même créé le script `scripts/07_explore_spacy_ner.py` pour explorer spaCy NER. Il est prêt à être utilisé et fait :
- Charge le modèle spaCy français (`fr_core_news_sm`)
- Teste sur 10 phrases de validation
- Compare avec la baseline
- Affiche les résultats détaillés

**Note** : Le script ne peut pas s'exécuter actuellement à cause du problème de compatibilité. Je le garde pour plus tard.

### Solutions possibles

J'ai plusieurs options :
1. **Utiliser Python 3.11 ou 3.12** (recommandé pour tester spaCy)
2. **Attendre une mise à jour de spaCy** compatible avec Python 3.14
3. **Passer directement à BERT** sans tester spaCy (recommandé pour la suite)

Pour l'instant, je vais continuer avec la baseline et passer directement au fine-tuning de BERT/CamemBERT.
