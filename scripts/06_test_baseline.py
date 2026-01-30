"""
Script de test simple pour la baseline sur quelques exemples.
"""

import json
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from models.baseline.baseline_model import BaselineModel


def load_cities():
    """Charge la liste des villes."""
    cities_file = Path("data/sncf/villes_list.json")
    with open(cities_file, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Teste la baseline sur quelques exemples."""
    print("=" * 60)
    print("TEST DE LA BASELINE")
    print("=" * 60)
    
    # Charger les villes
    cities = load_cities()
    print(f"Nombre de villes chargées : {len(cities)}")
    
    # Créer le modèle
    model = BaselineModel(cities)
    
    # Exemples de test
    test_cases = [
        "je voudrais aller de Toulouse à bordeaux",
        "Comment me rendre à Port-Boulet depuis la gare de Tours ?",
        "Je veux aller voir mon ami Albert à Tours en partant de Bordeaux",
        "Il y a-t-il des trains de Nantes à Montaigu",
        "Une phrase sans origine ni destination",
        "depuis paris je veux aller a albert pour boire un monaco.",
        "je veux faire saint denis saint etienne",
        "Je voudrais aller à Paris",
        "Je dois partir de Lyon"
    ]
    
    print("\n" + "=" * 60)
    print("RÉSULTATS DES TESTS")
    print("=" * 60)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest {i}: {text}")
        origin, destination, is_valid = model.extract_origin_destination(text)
        sentence_id, pred_origin, pred_dest = model.predict(i, text)
        
        print(f"  Origine détectée    : {origin}")
        print(f"  Destination détectée: {destination}")
        print(f"  Phrase valide       : {is_valid}")
        print(f"  Format sortie       : {sentence_id},{pred_origin},{pred_dest}")


if __name__ == "__main__":
    main()
