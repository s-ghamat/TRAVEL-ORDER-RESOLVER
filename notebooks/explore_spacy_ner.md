# Exploration spaCy NER

J'ai voulu explorer l'utilisation de spaCy pour la détection d'entités nommées (NER) sur les phrases du dataset, mais j'ai rencontré un problème.

## Problème de compatibilité

**Note importante** : Il y a un problème de compatibilité entre spaCy 3.8.11 et Python 3.14. Le modèle ne peut pas être chargé à cause d'une erreur dans pydantic v1.

**Solutions que je peux envisager** :
1. Utiliser Python 3.11 ou 3.12 (recommandé)
2. Attendre une mise à jour de spaCy compatible avec Python 3.14
3. Utiliser une version antérieure de spaCy (pas testé)

## Installation

```bash
pip install spacy
python -m spacy download fr_core_news_sm
```

**Note** : Si vous utilisez Python 3.14, l'installation peut échouer. Utilisez Python 3.11 ou 3.12.

## Script d'exploration

J'ai créé le script `scripts/07_explore_spacy_ner.py` pour explorer spaCy NER. Il est prêt et fait :
- Charge le modèle spaCy français
- Teste sur 10 phrases de validation
- Compare avec la baseline
- Affiche les résultats détaillés

**Utilisation** (quand le problème de compatibilité sera résolu) :
```bash
python scripts/07_explore_spacy_ner.py
```

## Utilisation basique (si spaCy fonctionne)

```python
import spacy
import json

# Charger le modèle français
nlp = spacy.load("fr_core_news_sm")

# Tester sur quelques phrases
test_phrases = [
    "je voudrais aller de Toulouse à bordeaux",
    "Comment me rendre à Port-Boulet depuis la gare de Tours ?",
    "Je veux aller voir mon ami Albert à Tours en partant de Bordeaux"
]

for phrase in test_phrases:
    doc = nlp(phrase)
    print(f"\nPhrase: {phrase}")
    print("Entités détectées:")
    for ent in doc.ents:
        print(f"  - {ent.text} ({ent.label_})")
```

## Résultats attendus

spaCy détecte généralement :
- **LOC** : Localisations (villes, pays)
- **GPE** : Entités géopolitiques (villes, pays, régions)
- **PER** : Personnes (prénoms)

## Avantages de spaCy

- Détection automatique des entités géographiques
- Gère les variations de casse
- Reconnaît les prénoms vs villes (dans certains cas)
- Modèle pré-entraîné, pas besoin d'entraînement

## Inconvénients

- Problème de compatibilité avec Python 3.14 (actuel)
- Nécessite un fine-tuning pour notre cas spécifique
- Peut confondre prénoms et villes (ex: "Albert")
- Ne distingue pas automatiquement origine/destination (il faut ajouter de la logique)
- Plus lent que la baseline basée sur les règles

## Comparaison avec la baseline

**Baseline basée sur les prépositions** :
- Plus adaptée à notre cas spécifique
- Utilise explicitement les prépositions pour distinguer origine/destination
- Utilise notre liste de villes SNCF
- Plus simple et plus rapide
- Fonctionne avec Python 3.14

**spaCy NER** :
- Détection automatique des entités géographiques
- Modèle pré-entraîné généraliste
- Nécessite une logique supplémentaire pour distinguer origine/destination
- Problème de compatibilité avec Python 3.14

## Recommandation

Pour le moment, étant donné le problème de compatibilité avec Python 3.14, je vais :
1. **Continuer avec la baseline** pour le premier follow-up
2. **Passer directement à BERT/CamemBERT** pour l'étape suivante (fine-tuning)
3. **Tester spaCy plus tard** si je change de version Python ou si spaCy est mis à jour

La baseline donne déjà de bons résultats (F1 de 70-86%) et peut servir de référence pour comparer avec BERT. C'est suffisant pour avancer.
