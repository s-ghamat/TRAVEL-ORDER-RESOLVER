"""
Script pour télécharger et traiter les données des gares SNCF depuis l'API Open Data.
"""

import requests
import json
from pathlib import Path
from typing import Dict, List, Set
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_sncf_stations() -> Dict:
    """
    Télécharge toutes les gares SNCF depuis l'API Open Data.
    
    Returns:
        Dict contenant toutes les données brutes de l'API
    """
    base_url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/gares-de-voyageurs/records"
    output_dir = Path("data/sncf")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_records = []
    limit = 100  # Nombre d'enregistrements par page
    offset = 0
    total_count = None
    
    logger.info("Début du téléchargement des données SNCF...")
    
    try:
        while True:
            params = {
                "limit": limit,
                "offset": offset
            }
            
            logger.info(f"Téléchargement des enregistrements {offset} à {offset + limit}...")
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Récupérer le total count lors de la première requête
            if total_count is None:
                total_count = data.get("total_count", 0)
                logger.info(f"Nombre total de gares à télécharger : {total_count}")
            
            records = data.get("results", [])
            if not records:
                break
            
            all_records.extend(records)
            logger.info(f"Enregistrements téléchargés : {len(all_records)}/{total_count}")
            
            # Vérifier si on a tout téléchargé
            if len(all_records) >= total_count:
                break
            
            offset += limit
            
            # Petite pause pour ne pas surcharger l'API
            import time
            time.sleep(0.5)
        
        result = {
            "total_count": total_count,
            "records": all_records
        }
        
        # Sauvegarder les données brutes
        raw_file = output_dir / "gares_raw.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Données brutes sauvegardées dans {raw_file}")
        logger.info(f"Total de {len(all_records)} gares téléchargées")
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors du téléchargement : {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue : {e}")
        raise


def analyze_structure(data: Dict) -> None:
    """
    Analyse la structure des données téléchargées.
    Affiche les clés principales et des exemples de données.
    
    Args:
        data: Dictionnaire contenant les données brutes
    """
    logger.info("=" * 60)
    logger.info("ANALYSE DE LA STRUCTURE DES DONNÉES")
    logger.info("=" * 60)
    
    records = data.get("records", [])
    if not records:
        logger.warning("Aucun enregistrement trouvé")
        return
    
    # Analyser le premier enregistrement pour voir la structure
    first_record = records[0]
    logger.info("\nStructure d'un enregistrement :")
    logger.info(json.dumps(first_record, indent=2, ensure_ascii=False)[:500] + "...")
    
    # Extraire les champs disponibles
    logger.info(f"\nColonnes disponibles :")
    for key in sorted(first_record.keys()):
        value = first_record[key]
        if isinstance(value, dict):
            value_preview = str(list(value.keys()))[:50]
        else:
            value_preview = str(value)[:50] if value else "None"
        logger.info(f"  - {key}: {value_preview}")
    
    # Afficher quelques exemples
    logger.info("\nExemples de gares (10 premières) :")
    for i, record in enumerate(records[:10], 1):
        nom = record.get("nom", "N/A")
        codeinsee = record.get("codeinsee", "N/A")
        codes_uic = record.get("codes_uic", "N/A")
        logger.info(f"  {i}. {nom} - Code INSEE: {codeinsee} - Code UIC: {codes_uic}")


def extract_cities_and_stations(data: Dict) -> tuple[List[str], List[Dict]]:
    """
    Extrait la liste des villes et gares depuis les données brutes.
    
    Args:
        data: Dictionnaire contenant les données brutes
        
    Returns:
        Tuple (liste_villes, liste_gares) où:
        - liste_villes: Liste des noms de villes uniques
        - liste_gares: Liste des gares avec détails
    """
    logger.info("=" * 60)
    logger.info("EXTRACTION DES VILLES ET GARES")
    logger.info("=" * 60)
    
    records = data.get("records", [])
    villes_set: Set[str] = set()
    gares_list: List[Dict] = []
    
    for record in records:
        # Extraire le nom de la gare (structure directe, pas dans record.fields)
        nom_gare = record.get("nom", "")
        if not nom_gare:
            continue
        
        # Extraire le code UIC
        code_uic = record.get("codes_uic", "")
        codeinsee = record.get("codeinsee", "")
        
        # Pour la ville, on utilise le nom de la gare
        # Beaucoup de gares ont le nom de la ville directement
        # Pour les gares avec noms composés, on extrait la partie principale
        ville = extract_city_from_station_name(nom_gare)
        
        # Normaliser le nom de la ville
        if ville:
            ville_normalisee = normalize_city_name(ville)
            villes_set.add(ville_normalisee)
        
        # Créer l'entrée pour la gare
        gare_info = {
            "nom_gare": nom_gare,
            "ville": ville_normalisee if ville else "",
            "nom_simple": extract_simple_name(nom_gare),
            "code_uic": code_uic if code_uic else "",
            "codeinsee": codeinsee if codeinsee else ""
        }
        gares_list.append(gare_info)
    
    villes_list = sorted(list(villes_set))
    
    logger.info(f"Nombre de villes uniques extraites : {len(villes_list)}")
    logger.info(f"Nombre de gares extraites : {len(gares_list)}")
    logger.info(f"\nExemples de villes (10 premières) : {villes_list[:10]}")
    
    return villes_list, gares_list


def normalize_city_name(city: str) -> str:
    """
    Normalise le nom d'une ville (capitalise, gère les tirets).
    
    Args:
        city: Nom de ville brut
        
    Returns:
        Nom de ville normalisé
    """
    if not city:
        return ""
    
    # Capitaliser chaque mot (gère les tirets)
    parts = city.split("-")
    normalized_parts = []
    
    for part in parts:
        part = part.strip()
        if part:
            # Capitaliser la première lettre, le reste en minuscules
            normalized = part[0].upper() + part[1:].lower() if len(part) > 1 else part.upper()
            normalized_parts.append(normalized)
    
    return "-".join(normalized_parts)


def extract_simple_name(full_name: str) -> str:
    """
    Extrait un nom simplifié depuis le nom complet de la gare.
    Ex: "Gare de Paris-Nord" -> "Paris-Nord"
    
    Args:
        full_name: Nom complet de la gare
        
    Returns:
        Nom simplifié
    """
    # Enlever "Gare de " au début
    if full_name.startswith("Gare de "):
        return full_name[8:]
    if full_name.startswith("Gare "):
        return full_name[5:]
    return full_name


def extract_city_from_station_name(station_name: str) -> str:
    """
    Extrait le nom de la ville depuis le nom de la gare.
    Ex: "Paris-Nord" -> "Paris", "Dijon" -> "Dijon", "Pont de Lignon" -> "Lignon"
    
    Args:
        station_name: Nom de la gare
        
    Returns:
        Nom de la ville extrait
    """
    # Enlever "Gare de " si présent
    name = extract_simple_name(station_name)
    
    # Si le nom contient un tiret, prendre la partie avant le tiret
    # (ex: "Paris-Nord" -> "Paris", "Saint-Denis" -> "Saint-Denis")
    if "-" in name:
        parts = name.split("-")
        # Prendre la première partie (sauf si c'est "Saint" ou "Port")
        if parts[0].lower() in ["saint", "sainte", "port", "pont"]:
            return "-".join(parts[:2]) if len(parts) > 1 else parts[0]
        return parts[0]
    
    # Si le nom contient " de " ou " du " ou " des ", prendre la partie après
    # (ex: "Pont de Lignon" -> "Lignon")
    if " de " in name.lower():
        parts = name.split(" de ", 1)
        if len(parts) > 1:
            return parts[1].split()[0]  # Prendre le premier mot après "de"
    
    # Sinon, retourner le nom tel quel (ex: "Dijon", "Lyon")
    return name


def save_processed_data(cities_list: List[str], stations_list: List[Dict]) -> None:
    """
    Sauvegarde les données traitées dans des fichiers JSON.
    
    Args:
        cities_list: Liste des villes uniques
        stations_list: Liste des gares avec détails
    """
    output_dir = Path("data/sncf")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder la liste des villes
    villes_file = output_dir / "villes_list.json"
    with open(villes_file, "w", encoding="utf-8") as f:
        json.dump(cities_list, f, ensure_ascii=False, indent=2)
    logger.info(f"Liste des villes sauvegardée dans {villes_file}")
    
    # Sauvegarder la liste des gares
    gares_file = output_dir / "gares_list.json"
    with open(gares_file, "w", encoding="utf-8") as f:
        json.dump(stations_list, f, ensure_ascii=False, indent=2)
    logger.info(f"Liste des gares sauvegardée dans {gares_file}")


def identify_ambiguous_cities(cities_list: List[str]) -> List[str]:
    """
    Identifie les villes qui pourraient être ambiguës (prénoms, mots communs).
    
    Args:
        cities_list: Liste des villes
        
    Returns:
        Liste des villes potentiellement ambiguës
    """
    # Liste de prénoms communs français
    common_names = {
        "Albert", "Paris", "Lourdes", "Florence", "Valence", "Angers",
        "Bernard", "Claude", "Denis", "Étienne", "François", "Henri",
        "Jean", "Louis", "Marc", "Marie", "Michel", "Pierre", "Paul"
    }
    
    ambiguous = []
    for city in cities_list:
        # Vérifier si le nom de ville est aussi un prénom
        if city in common_names:
            ambiguous.append(city)
    
    logger.info(f"\nVilles potentiellement ambiguës (prénoms) : {len(ambiguous)}")
    if ambiguous:
        logger.info(f"Exemples : {ambiguous[:10]}")
    
    return ambiguous


def main():
    """Fonction principale."""
    try:
        # 1. Télécharger les données
        logger.info("Étape 1/4 : Téléchargement des données SNCF")
        data = fetch_sncf_stations()
        
        # 2. Analyser la structure
        logger.info("\nÉtape 2/4 : Analyse de la structure")
        analyze_structure(data)
        
        # 3. Extraire villes et gares
        logger.info("\nÉtape 3/4 : Extraction des villes et gares")
        cities_list, stations_list = extract_cities_and_stations(data)
        
        # Identifier les villes ambiguës
        ambiguous = identify_ambiguous_cities(cities_list)
        
        # 4. Sauvegarder les données traitées
        logger.info("\nÉtape 4/4 : Sauvegarde des données traitées")
        save_processed_data(cities_list, stations_list)
        
        # Sauvegarder aussi la liste des villes ambiguës
        if ambiguous:
            output_dir = Path("data/sncf")
            ambiguous_file = output_dir / "villes_ambiguës.json"
            with open(ambiguous_file, "w", encoding="utf-8") as f:
                json.dump(ambiguous, f, ensure_ascii=False, indent=2)
            logger.info(f"Liste des villes ambiguës sauvegardée dans {ambiguous_file}")
        
        logger.info("\n" + "=" * 60)
        logger.info("TÉLÉCHARGEMENT TERMINÉ AVEC SUCCÈS")
        logger.info("=" * 60)
        logger.info(f"Total gares : {len(stations_list)}")
        logger.info(f"Total villes : {len(cities_list)}")
        logger.info(f"Villes ambiguës : {len(ambiguous)}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution : {e}")
        raise


if __name__ == "__main__":
    main()
