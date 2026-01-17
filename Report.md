# Rapport PDF — Travel Order Resolver (NLP + SNCF)

## 0) Résumé 

Ce projet implémente un **Travel Order Resolver** en français : à partir d’une commande textuelle (format `sentenceID,sentence`), le système **détecte si la phrase est une demande de trajet**, extrait **ville/gare de départ** et **ville/gare d’arrivée**, puis produit **un itinéraire** basé sur des **horaires SNCF** (GTFS).
Le cœur du projet est le **module NLP**, évalué quantitativement sur jeux de test (manuel + synthétique bruité 10k) et comparé à une approche spaCy NER.

---

## 1) Objectifs et périmètre

### 1.1 Objectif principal

* Lire des ordres de trajets au format `sentenceID,sentence`
* Produire :

  * soit `sentenceID,Departure,Destination`
  * soit `sentenceID,INVALID`
* Puis, à partir du triplet, produire une route :

  * `sentenceID,Departure,Step1,Step2,...,Destination`
* Et fournir une preuve “horaires” SNCF (GTFS) : départ/arrivée, identifiant de trip

### 1.2 Hypothèses

* Entrées en français, bruitées (accents manquants, fautes, absence de majuscules)
* Le système doit **rejeter** en cas d’ambiguïté plutôt que “inventer”

---

## 2) Architecture globale (schéma + description)

### 2.1 Vue d’ensemble (couches)

1. **I/O CLI (conforme au sujet)**

   * Lecture stdin : `sentenceID,sentence`
2. **NLP Resolver**

   * Baseline (règles + normalisation + fuzzy)
   * spaCy (EntityRuler, NER “STATION/CITY-like”)
3. **Station Layer (SNCF gares)**

   * Dataset “Gares de voyageurs” nettoyé (`stations_clean.csv`)
   * Désambiguïsation des gares dans une ville (Paris, Lyon, etc.)
4. **Pathfinder (horaires SNCF)**

   * GTFS SNCF (stops, trips, stop_times)
   * Recherche d’un itinéraire **direct** puis **1 correspondance**
5. **Sorties**

   * Ligne route strictement conforme : `sentenceID,Departure,Step...,Destination`
   * Ligne “SCHEDULE” (preuve horaires) : temps + trip_id + stop_names

### 2.2 Données utilisées

* **SNCF Stations**

  * `data/sncf_clean/stations_clean.csv`
  * `station_name, uic_code, latitude, longitude`
* **SNCF GTFS (horaires théoriques)**

  * `data/gtfs_sncf/stops.txt, stop_times.txt, trips.txt, routes.txt, ...`
* **Datasets NLP**

  * eval manuel (petit)
  * `synthetic_10k.csv` bruité (10 000)

---

## 3) NLP — Baseline (solution sécurisée)

### 3.1 Normalisation

* minuscules
* suppression d’accents (si nécessaire)
* nettoyage ponctuation
* espaces multiples

### 3.2 Extraction (règles)

* patrons avec prépositions : `de / depuis / à / vers`
* gestion d’ordres variés (ex: “billet Toulouse Paris”)
* rejet si ordre incomplet ou ambigu

### 3.3 Fuzzy matching contrôlé

* correction des fautes simples sur noms de villes
* limite stricte pour éviter les “hallucinations” (pas de correction agressive)

### 3.4 Stratégie de rejet

* Si ambigu/incomplet : `INVALID`
* En mode “Helpful” (application) : proposition de candidats SNCF pour sélectionner

---

## 4) NLP — Approche spaCy (NER)

### 4.1 Motivation

Tester une approche NER “library-first” comme étape intermédiaire avant un modèle entraîné.

### 4.2 Implémentation

* `spacy.blank("fr")` + `EntityRuler`
* Patterns générés à partir des noms de gares SNCF
* Label custom (ex: STATION)
* Extraction des deux entités pertinentes

### 4.3 Limites observées

* Moins robuste au bruit / fautes
* Moins performant si entités non reconnues

---

## 5) Pathfinder — Horaires SNCF (GTFS)

### 5.1 Objectif

À partir de `Departure,Destination` :

* trouver au moins une ligne d’itinéraire satisfaisante
* utiliser des horaires SNCF réels (GTFS)

### 5.2 Méthode (explicable)

1. Mapping ville → “hub station”

   * scoring (Paris → “Gare de Lyon”, Lyon → “Part-Dieu”, etc.)
2. Mapping UIC → GTFS stops

   * utilisation de `stop_code` (UIC 8 chiffres) + fallback
3. Recherche itinéraire

   * direct : même trip_id contenant les deux stops dans l’ordre
   * 1 correspondance : deux legs reliés par un stop commun, contrainte `dep2 >= arr1`

### 5.3 Complexité (discussion courte)

* Direct : jointure sur trip_id (efficace)
* 1 correspondance : join sur transfer_stop_id + filtrage temporel (plus coûteux)
* Optimisation possible : réduire candidats stops, indexer stop_times, cache

---

## 6) Exemple détaillé “end-to-end” (obligatoire)

### Entrée

`S42,Je voudrais aller de Paris à Lyon demain`

### Étapes

1. **NLP** (baseline ou spaCy)

   * extrait : Departure=Paris, Destination=Lyon
2. **Pathfinder (GTFS)**

   * sélection hubs : Paris Gare de Lyon / Lyon Part-Dieu
   * recherche direct → trouvé
3. **Sorties**

* Ligne route (spécification) :
  `S42,Paris,Lyon`
* Ligne horaires (preuve) :
  `S42,SCHEDULE,DIRECT,Paris,Lyon,06:16:00,08:22:00,<trip_id>,Paris Gare de Lyon...,Lyon Part Dieu`

---

## 7) Évaluation & résultats (NLP)

### 7.1 Protocole

* Baseline vs spaCy
* Mesure “OK vs INVALID” sur dataset synthétique bruité 10k
* Le but : robustesse à la diversité des structures + fautes + bruit

### 7.2 Résultats (10k synthétique)

| Modèle                    |                   OK |              INVALID |
| ------------------------- | -------------------: | -------------------: |
| Baseline (règles + fuzzy) | 4001 / 10000 (40.0%) | 5999 / 10000 (60.0%) |
| spaCy (EntityRuler)       | 2723 / 10000 (27.2%) | 7277 / 10000 (72.8%) |

Causes principales :

* baseline : `invalid_or_ambiguous`
* spaCy : `spacy_no_result`

### 7.3 Interprétation (le paragraphe “fort” demandé)

**Pourquoi spaCy est moins bon que le baseline ?**
L’approche spaCy basée sur EntityRuler dépend fortement de la reconnaissance exacte des entités. Sur des phrases bruitées (accents manquants, casse aléatoire, fautes), le NER rate plus souvent au moins une des deux entités, ce qui force un rejet. À l’inverse, le baseline encode explicitement des relations syntaxiques (prépositions, ordre relatif, patrons fréquents) et bénéficie d’un fuzzy matching contrôlé, ce qui le rend plus robuste sur les fautes “simples”.

**Pourquoi le rejet en cas d’ambiguïté est intentionnel ?**
Dans un contexte de planification de trajet, confondre départ et arrivée (ou choisir une gare au hasard dans une ville très ambiguë comme Paris) produit une réponse incorrecte et trompeuse. Le système préfère donc retourner `INVALID` (ou déclencher un mode “Helpful” de désambiguïsation) plutôt que d’inventer un résultat : c’est un choix de sûreté et de fiabilité.

---

## 8) Justification (si vous ne faites pas de fine-tuning BERT)

Même si des modèles type CamemBERT peuvent améliorer la reconnaissance, le projet est principalement évalué sur la qualité NLP et la méthodologie (données, métriques, robustesse, expérimentation). Ici, nous avons sécurisé une solution robuste et explicable (baseline), testé une approche NER (spaCy), et intégré des horaires SNCF réels (GTFS). Une fine-tune transformer est identifiée comme amélioration future, mais nécessite un dataset annoté plus conséquent et une phase d’entraînement contrôlée (hyperparamètres, validation croisée, etc.).

---

## 9) Guide d’exécution (à inclure dans le PDF)

### NLP seul (stdin)

```bash
PYTHONPATH=".:src" python -m tor.cli
```

### Pathfinder GTFS (triplet)

```bash
echo "S1,Paris,Lyon" | PYTHONPATH=".:src" python -m tor.gtfs_pathfinder_cli
```

### Pipeline complet (NLP → horaires)

```bash
echo "S42,Je voudrais aller de Paris à Lyon demain" | ./scripts/run_pipeline_with_schedules.sh
```

---

## 10) Limites & améliorations (courte liste)

* Itinéraires > 1 correspondance (possible extension)
* Gestion robuste des “intermediate stops” (“en passant par …”)
* Dataset annoté collaboratif + fine-tuning CamemBERT
* Amélioration de la sélection automatique de gares (utiliser fréquence/centralité)
* Indexation/caching GTFS pour performance
