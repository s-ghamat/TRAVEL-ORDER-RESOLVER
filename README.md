# C1 — Application NLP + Données (SNCF) : architecture, méthode, UI et améliorations

## Objectif

L’objectif est de transformer un extracteur d’ordres de voyage en français (Départ / Arrivée) en une application démontrable, tout en conservant un cœur NLP isolé et évalué. L’application doit gérer un problème réel lié aux données SNCF : **une ville ne correspond pas à une seule gare**, et les entrées utilisateur sont souvent **incomplètes ou ambiguës**.

---

## 1) Architecture du projet (séparation claire des responsabilités)

Le projet est organisé en couches :

* **`src/tor/` (cœur “noté”)**

  * `nlp.py` : résolveur **baseline** (règles + normalisation + fuzzy matching) qui renvoie `(departure, arrival)` ou `None` (INVALID).
  * `spacy_resolver.py` : résolveur **spaCy NER** (EntityRuler) qui extrait des entités `CITY` à partir de `data/cities.txt`, puis déduit la paire (départ, arrivée).
  * Cette couche reste indépendante de l’UI : elle est testable via scripts/CLI.

* **`api/` (couche application / orchestration)**

  * `resolver_service.py` : wrapper unifié `resolve_sentence(sentence, mode, helpful)` qui :

    * appelle baseline ou spaCy,
    * calcule un **score de confiance** (explainable),
    * propose une **désambiguïsation** à partir des données SNCF,
    * active un **mode “Helpful”** (fallback interactif au lieu de INVALID).
  * `stations.py` : chargement et recherche dans `data/sncf_clean/stations_clean.csv` (gares SNCF nettoyées).
  * `pathfinder.py` : construction d’un itinéraire en **séquence de points** (gares) et calcul de distance (Haversine) entre étapes.

* **`ui/` (démonstrateur Streamlit)**

  * `ui/app.py` : interface utilisateur (texte → extraction → sélection gares → carte → itinéraire).

Cette structure répond à l’exigence “garder le NLP isolé” : le cœur NLP peut être évalué indépendamment, et l’application n’est qu’une couche au-dessus.

---

## 2) Données SNCF et motivation “ville ≠ gare”

Les données SNCF “Gares de voyageurs” ont été nettoyées et normalisées pour produire un fichier exploitable :

* `data/sncf_clean/stations_clean.csv`
* Colonnes : `station_name`, `uic_code`, `latitude`, `longitude` (et trigram selon nettoyage)

Ce dataset met en évidence un problème réel :

* une requête comme **“Lyon”** renvoie plusieurs gares : *Lyon Part-Dieu, Lyon Perrache, Lyon Vaise, …*
* certaines chaînes (“Gare de Lyon”) peuvent introduire des confusions lexicales (ex: *Paris Gare de Lyon*).

L’application traite explicitement cette ambiguïté via la **désambiguïsation station-level**.

---

## 3) Résolution NLP : deux approches + mode Helpful

### 3.1 Baseline (règles)

* Détection de patrons (“de X à Y”, “depuis X vers Y”, etc.)
* Normalisation (casse, ponctuation, accents)
* Fuzzy matching contrôlé pour corriger des fautes (ex: Parys → Paris)
* Rejet des cas incomplets/ambiguës → `INVALID`

### 3.2 Approche spaCy NER (EntityRuler)

* Pipeline spaCy léger `spacy.blank("fr")`
* `EntityRuler` avec patterns issus de `data/cities.txt`
* Extraction des villes (label `CITY`) puis heuristique sur l’ordre (ex: “de X à Y”)

### 3.3 “Helpful mode”

Différence majeure vs un système qui retourne seulement INVALID :

* Si le NLP ne produit pas de paire (départ/arrivée), le système propose un **fallback** :

  * extraction de **candidats de gares** depuis le texte brut (token hits)
  * question de clarification : l’utilisateur choisit départ/arrivée parmi les suggestions
* Résultat : l’application “récupère” des requêtes imparfaites au lieu d’échouer.

---

## 4) Désambiguïsation : sélection de gares SNCF (feature différenciante)

Après extraction de villes (Paris / Lyon), l’application calcule des **candidats de gares** via `stations_clean.csv` :

* substring word-boundary match + ranking (gare, hubs, nom canonique)
* l’utilisateur choisit la gare exacte via dropdowns :

  * exemple : “Paris” → *Gare de Lyon / Gare du Nord / Montparnasse / …*
  * exemple : “Lyon” → *Part-Dieu / Perrache / …*

Cela rend l’application plus réaliste qu’un simple “city-to-city”.

---

## 5) Itinéraire : séquence de points + carte

Une fois les gares choisies :

* `pathfinder.build_itinerary()` retourne une **liste ordonnée de points** :

  * Départ → (via optional) → Arrivée
* calcul des distances entre étapes (Haversine)
* affichage :

  * tableau des étapes
  * carte (Streamlit `st.map`) avec positions des gares

Cette partie remplit la logique “application” même avant d’intégrer des horaires temps réel.

---

## 6) Score de confiance (explainable) + analyse d’erreurs

Le score de confiance est conçu pour être **interprétable** (utile en démonstration) :

* signal de base : présence littérale des villes dans la phrase

  * `both_literal / one_literal / none_literal`
* pénalité d’ambiguïté : plus il y a de gares candidates, plus la confiance baisse
* pénalité de contamination : si des gares candidates “contiennent” lexicalement l’autre ville (ex: “Paris …” dans liste de Lyon), la confiance baisse

Exemple observé (spaCy) :

* `both_literal = True`
* `departure_candidates_count = 7`, `arrival_candidates_count = 8`
* `ambiguity_penalty = 0.18`
* `contamination_penalty = 0.10`

Ce mécanisme explique clairement au jury pourquoi la confiance diminue dans certains cas.

---

## 7) Ce qui différencie l’application (UI/UX)

Contrairement à une UI “texte → résultat final” standard, l’UX est orientée **résolution progressive** :

1. extraction villes + score + debug
2. désambiguïsation gare-level (choix explicite)
3. itinéraire en étapes + carte
4. mode Helpful : questions + sélection en cas d’échec NLP

Ainsi l’application traite un problème SNCF concret : **la granularité station** et l’ambiguïté.

---

## 8) Pistes d’amélioration (facultatif)

* Intégrer une API horaires SNCF / Navitia pour afficher les prochains trains entre gares choisies
* Étendre les patterns spaCy (stations directement, pas seulement villes)
* Ajouter une gestion explicite des “via” dans le parsing NLP (ex: “en passant par Dijon”)
* Caching des résultats station search et optimisation du ranking
