"""
Script optionnel pour analyser la structure des données SNCF téléchargées.
Affiche des statistiques et des informations sur les données.
"""

import json
from pathlib import Path
from collections import Counter

def analyze_sncf_data():
    """Analyse les données SNCF et affiche des statistiques."""
    
    data_dir = Path("data/sncf")
    
    # Charger les données
    with open(data_dir / "villes_list.json", "r", encoding="utf-8") as f:
        villes = json.load(f)
    
    with open(data_dir / "gares_list.json", "r", encoding="utf-8") as f:
        gares = json.load(f)
    
    with open(data_dir / "villes_ambiguës.json", "r", encoding="utf-8") as f:
        villes_ambiguës = json.load(f)
    
    print("=" * 60)
    print("STATISTIQUES DES DONNÉES SNCF")
    print("=" * 60)
    
    print(f"\nResume general :")
    print(f"  - Nombre total de gares : {len(gares)}")
    print(f"  - Nombre de villes uniques : {len(villes)}")
    print(f"  - Villes potentiellement ambigues : {len(villes_ambiguës)}")
    
    print(f"\nVilles ambigues (prenoms) :")
    for ville in villes_ambiguës:
        print(f"  - {ville}")
    
    print(f"\nExemples de villes majeures :")
    villes_majeures = ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes", "Lille", "Strasbourg"]
    for ville_majeure in villes_majeures:
        # Chercher les variantes
        variantes = [v for v in villes if ville_majeure.lower() in v.lower()]
        if variantes:
            print(f"  - {ville_majeure} : {len(variantes)} variante(s) - {variantes[:3]}")
    
    print(f"\nExemples de gares :")
    for i, gare in enumerate(gares[:5], 1):
        print(f"  {i}. {gare['nom_gare']} ({gare['ville']}) - UIC: {gare['code_uic']}")
    
    # Statistiques sur les codes UIC
    gares_avec_uic = [g for g in gares if g['code_uic']]
    print(f"\nCodes UIC :")
    print(f"  - Gares avec code UIC : {len(gares_avec_uic)}/{len(gares)}")
    
    # Statistiques sur les codes INSEE
    gares_avec_insee = [g for g in gares if g['codeinsee']]
    print(f"  - Gares avec code INSEE : {len(gares_avec_insee)}/{len(gares)}")
    
    print("\n" + "=" * 60)
    print("Analyse terminée !")
    print("=" * 60)

if __name__ == "__main__":
    analyze_sncf_data()
